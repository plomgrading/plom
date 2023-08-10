# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import pandas as pd

from argparse import RawTextHelpFormatter
from django.core.management.base import BaseCommand
import matplotlib.pyplot as plt
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

The data is read from media/marks.csv. This file must have the question marks
labelled as q1_mark, q2_mark, etc. The data is allowed to have NaN values, but
these rows will be dropped before performing PCA. The file's first column must
be the identifier for the student/paper.

The output is the explained variance ratio and the principal components.
Where the explained variance ratio is the percentage of variance explained by
each of the selected components. The principal components are the new variables
that are a linear combination of the original variables.

Example usage:
python3 manage.py PCA_analysis 2
python3 manage.py PCA_analysis 2 --of-students
"""


class Command(BaseCommand):
    help = HELP_TEXT

    sms = StudentMarkService()
    spec = Specification.load()

    print("Loading data from media/marks.csv")
    student_marks = pd.read_csv("media/marks.csv")
    clean_student_df = student_marks.dropna()
    question_df = clean_student_df.filter(regex="q[0-9]*_mark")

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

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
        index = self.question_df.index
        columns = self.question_df.columns
        if not options["of_students"]:
            # transpose the data to perform PCA on the questions
            data = data.T
            index = self.question_df.columns
            columns = self.question_df.index

        if num_components > min(data.shape[0], data.shape[1]):
            print(
                f"The number of components must be between 0 and min(n_samples, n_features)={min(data.shape[0], data.shape[1])}"
            )
            return

        print(f"Performing PCA on {data.shape[0]} rows and {data.shape[1]} columns")
        print("See python3 manage.py PCA_analysis --help for more information on PCA\n")
        print("Raw data:")
        print(pd.DataFrame(data, index=index, columns=columns))
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
            principalComponents,
            columns=[f"PC{i}" for i in range(num_components)],
            index=index,
        )

        # add a linear combination of the principal components to the dataframe as the last column
        principalDf["PC_linear_comb"] = principalDf.dot(pca.explained_variance_ratio_)
        print(principalDf)
        print("")

        # plot first 2 principal components using matplotlib
        if num_components >= 2:
            plt.scatter(
                principalDf["PC0"],
                principalDf["PC1"],
            )
            row_labels = principalDf.index.tolist()
            for txt in row_labels:
                plt.text(principalDf["PC0"][txt] + 0.1, principalDf["PC1"][txt], txt)
            plt.scatter(principalDf["PC0"], principalDf["PC1"])
            plt.xlabel("PC0")
            plt.ylabel("PC1")
            plt.savefig("media/PCA_plot.png")
            print("PCA plot saved to media/PCA_plot.png")
