# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import pandas as pd

from argparse import RawTextHelpFormatter
from django.core.management.base import BaseCommand
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from Finish.services import StudentMarkService
from Papers.models import Specification


HELP_TEXT = """
Perform PCA analysis on the per question marks.

PCA stands for Principal Component Analysis. It is a method of dimensionality
reduction. It is used to reduce the number of variables in a dataset while
preserving as much information as possible. It does this by creating new
variables that are a linear combination of the original variables. These new
variables are called principal components.

This command performs PCA on the question marks per student. It can also
perform PCA on the students if the --of-students flag is used. The number of
components to use is specified by the num_components argument.

The output is the explained variance ratio and the principal components.
Where the explained variance ratio is the percentage of variance explained by
each of the selected components. The principal components are the new variables
that are a linear combination of the original variables.

Example usage:
python3 manage.py PCA_analysis 2
python3 manage.py PCA_analysis 2 --of-students
"""


class Command(BaseCommand):
    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    help = HELP_TEXT

    sms = StudentMarkService()
    spec = Specification.load()

    student_dict = sms.get_all_students_download(
        version_info=True, timing_info=False, warning_info=False
    )
    student_keys = sms.get_csv_header(
        spec, version_info=True, timing_info=False, warning_info=False
    )
    student_df = pd.DataFrame(student_dict, columns=student_keys)
    clean_student_df = student_df.dropna()
    question_df = clean_student_df.filter(regex="q[0-9]*_mark")

    def add_arguments(self, parser):
        parser.add_argument(
            "num_components", type=int, help="Number of PCA components to use"
        )
        parser.add_argument(
            "--of-students",
            action="store_true",
            default=False,
            help="Perform PCA of the student, default is to perform PCA of the questions",
        )

    def handle(self, *args, **options):
        num_components = options["num_components"]

        data = self.question_df.loc[:, :].values
        if not options["of_students"]:
            # transpose the data to perform PCA on the questions
            data = data.T

        print(f"Performing PCA on {data.shape[0]} rows and {data.shape[1]} columns")
        print("See python3 manage.py PCA_analysis --help for more information on PCA\n")
        print("Raw data:")
        print(data)
        print("")

        try:
            norm_data = StandardScaler().fit_transform(data)
        except ValueError:
            print("No data to analyse")
            return

        feat_cols = [f"feature{i}" for i in range(norm_data.shape[1])]
        df = pd.DataFrame(norm_data, columns=feat_cols)

        pca = PCA(n_components=num_components)
        principalComponents = pca.fit_transform(df)

        print(
            f"Explained variance ratio (Eigenvalues): {pca.explained_variance_ratio_}\n"
        )
        principalDf = pd.DataFrame(
            principalComponents, columns=[f"PC{i}" for i in range(num_components)]
        )

        # add a linear combination of the principal components to the dataframe as the last column
        principalDf["PC_linear_comb"] = principalDf.dot(pca.explained_variance_ratio_)

        print(principalDf)
