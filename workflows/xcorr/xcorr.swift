
/*
  XCORR SWIFT
  Main cross-correlation workflow
*/

import files;
import io;
import python;
import unix;

printf("XCORR WORKFLOW");

string studies[] = file_lines(input("studies.txt"));
string rna_seq_data = "./test_data/combined_rnaseq_data_lincs1000_combat.bz2";
string drug_response_data = "./test_data/rescaled_combined_single_drug_growth_100K";
int cutoffs[][] = [[200, 100],
                   [100, 50],
                   [400, 200],
                   [200, 50],
                   [400, 50],
                   [400, 100]];

app uno(file features)
{
  "./uno.sh" features ;
}

init_xcorr() =>
{
  foreach study1 in studies
  {
    foreach study2 in studies
    {
      if (study1 != study2)
      {
        foreach cutoff in cutoffs
        {
          printf("Study1: %s, Study2: %s, cc: %d, ccc: %d",
                 study1, study2, cutoff[0], cutoff[1]);
          fname = "./test_data/%s_%s_%d_%d_features.txt" %
                   (study1, study2, cutoff[0], cutoff[1]);
          file features<fname>;
          compute_feature_correlation(study1, study2, cutoff[0], cutoff[1], fname) =>
            features = touch();
          uno(features);
        }
      }
    }
  }
}

(void o)
init_xcorr() {
  init_template =
"""
import uno_xcorr
from xcorr_db import xcorr_db

DB = xcorr_db('xcorr.db')
DB.read_feature_names()
DB.read_study_names()
rna_seq_data = '%s'
drug_response_data = '%s'

uno_xcorr.init_uno_xcorr(rna_seq_data, drug_response_data)
""";

  init_code = init_template % (rna_seq_data, drug_response_data);
  python_persist(init_code, "''") =>
  o = propagate();
}

(void v)
compute_feature_correlation(string study1, string study2, int corr_cutoff, int xcorr_cutoff, string features_file)
{
  log_corr_template =
"""
features = DB.scan_features_file('%s')
DB.insert_xcorr_record(studies=[ '%s', '%s' ],
                       features=features,
                       cutoff_corr=%d, cutoff_xcorr=%d)
""";

  xcorr_template =
"""
import uno_xcorr

study1 = '%s'
study2 = '%s'
correlation_cutoff = %d
cross_correlation_cutoff = %d
features_file = '%s'
uno_xcorr.coxen_feature_selection(study1, study2, correlation_cutoff, cross_correlation_cutoff, output_file=features_file)
""";

  log_code = log_corr_template % (features_file, study1, study2, corr_cutoff, xcorr_cutoff);
  python_persist(log_code, "''");

  code = xcorr_template % (study1, study2, corr_cutoff, xcorr_cutoff, features_file);
  python_persist(code, "''") =>
    v = propagate();
}


// Selected features = best N features between A and B based on correlation
