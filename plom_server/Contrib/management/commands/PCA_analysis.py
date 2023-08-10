# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import pandas as pd

from django.core.management.base import BaseCommand
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from Finish.services import StudentMarkService
from Papers.models import Specification


class Command(BaseCommand):
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
        if options["of_students"]:
            # transpose the data to perform PCA on the students
            data = data.T

        try:
            norm_data = StandardScaler().fit_transform(data)
        except ValueError:
            print("No data to analyse")
            return

        feat_cols = [f"feature{i}" for i in range(norm_data.shape[1])]
        df = pd.DataFrame(norm_data, columns=feat_cols)

        pca = PCA(n_components=num_components)
        principalComponents = pca.fit_transform(df)

        print(f"Explained variance ratio: {pca.explained_variance_ratio_}")
        principalDf = pd.DataFrame(
            principalComponents, columns=[f"PC{i}" for i in range(num_components)]
        )
        print(principalDf)
