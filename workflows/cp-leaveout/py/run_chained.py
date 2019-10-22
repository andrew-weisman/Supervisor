import subprocess
import os
import json
import sys
import io
import argparse

import plangen

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=str, default='plan.json',
                        help='plan data file')
    parser.add_argument('--nodes', type=int, default=1,
                        help='number of nodes to execute each stage')
    parser.add_argument('--stages', type=int, default=1,
                        help='number of stages to run')
    parser.add_argument('--upf_dir', type=str, default=None, required=True,
        help='the output directectory for the generated upf files')
    parser.add_argument('--site', type=str, default=None, required=True,
        help='the hpc site (e.g. summit)')
    parser.add_argument('--submit_script', type=str, default=None, required=True,
        help='the script to submit the job for each stage')

    return parser.parse_args()

def parse_run_vars(outs):
    to_prefix = 'TURBINE_OUTPUT='
    job_id_prefix = 'JOB_ID='
    str_io = io.StringIO(outs)
    turbine_output = ''
    job_id = ''
    for line in str_io.readlines():
        line = line.strip()
        if line.startswith(to_prefix):
            turbine_output = line[len(to_prefix) : ]
        elif line.startswith(job_id_prefix):
            job_id = line[len(job_id_prefix) : ]
            
    return (turbine_output, job_id)


def run_script(script, args):
    cmd = [script] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # stderr is redirected to stdout
    outs, _ = p.communicate()
    return outs.decode('utf-8')

def run_upfs(upfs, submit_script, site, plan_file):
    job_id = None
    turbine_output = None
    for i, upf in enumerate(upfs):
        # UPFS are in stage order
        args = [site, '-a', 'cfg-sys-s{}.sh'.format(i + 1), plan_file, upf, str(i + 1)]
        if job_id:
            args += [turbine_output, '#BSUB -w done({})'.format(job_id)]
        else:
            args += ['job0', '## JOB 0']
            
        outs = run_script(submit_script, args)
        turbine_output, job_id = parse_run_vars(outs)
        exp_id = os.path.basename(turbine_output)
        print('\n########### JOB {} - {} - {} ##############'.format(i,exp_id, job_id))
        print("Running: {} {}".format(submit_script, ' '.join(args)))
        print('{}'.format(outs))
        print('TURBINE_OUTPUT: {}'.format(turbine_output))
        print('JOB_ID: {}\n'.format(job_id))
        if not job_id:
            print("JOB_ID NOT FOUND - ABORTING RUNS")
            break

def get_plan_info(plan_file):
    plan_dict = plangen.load_plan(plan_file)
    # key of first entry is the root node
    iter_pd = iter(plan_dict)
    root_node = next(iter_pd)
    total_stages = -1
    total_nodes = -1
    for k in iter_pd:
        # has skipped the root node, so we can get 
        # the second element in val
        vals = (k.split("."))
        n_vals = len(vals)
        total_stages = max(total_stages, n_vals)
        total_nodes = max(total_nodes, int(vals[1]))
    
    return (root_node, total_stages, total_nodes)

def generate_upfs(prefix, upf_dir, root_node, n_stages, n_nodes):
    parents = [root_node]
    upf_prefix = '{}/{}_'.format(upf_dir, prefix)
    upfs = []
    counts = []
    for s in range(1, n_stages + 1):
        upf_path = '{}s{}_upf.txt'.format(upf_prefix, s)
        result = generate_stage(parents, n_nodes, upf_path)
        upfs.append(result[0])
        counts.append(result[1])

    return (upfs, counts)

def generate_stage(parents, n_nodes, f_path):
    children = []
    c = 0
    with open(f_path, 'w') as f_out:
        for p in parents:
            for n in range(1, n_nodes + 1):
                child = '{}.{}'.format(p, n)
                f_out.write('{}\n'.format(child))
                # TODO write children
                children.append(child)
                c += 1
    # print('Stage {}: {}'.format(stage, ' '.join(children)))
    return (children, c)
   

def run(args):
    plan_file = args.plan
    n_nodes = args.nodes
    n_stages = args.stages

    root_node, total_stages, total_nodes = get_plan_info(plan_file)
    if n_nodes == -1 or n_nodes > total_nodes:
        n_nodes = total_nodes
    if n_stages == -1 or n_stages >= total_stages:
        n_stages = total_stages

    prefix = os.path.splitext(os.path.basename(plan_file))[0]
    upfs, counts = generate_upfs(prefix, args.upf_dir, root_node, n_stages, n_nodes)
    print("Submitting {} jobs for stages: {}, nodes: {}".format(n_stages - 1, n_stages - 1, n_nodes))
    for i, c in enumerate(counts):
        print("\tStage: {}, UPF: {}, Model Runs: {}".format(i + 1, upfs[i], c))

    run_upfs(upfs, args.submit_script, args.site, plan_file)

if __name__ == "__main__":
    args = parse_arguments()
    run(args)
