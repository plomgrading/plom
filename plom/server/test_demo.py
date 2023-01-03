# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2022 Natalie Balashov

import os
from pathlib import Path
from shlex import split
import subprocess

from pytest import raises

from plom.server import PlomLiteDemoServer
from plom.plom_exceptions import PlomConflict


def setup_module(module):
    # TODO: get a random port from OS instead?
    module.Test.demo = PlomLiteDemoServer(port=41981)
    module.Test.env = {**os.environ, **module.Test.demo.get_env_vars()}


def teardown_module(module):
    module.Test.demo.stop()


class Test:
    # pylint: disable=no-member
    def test_its_alive(self):
        assert self.demo.process_is_running()

    def test_has_pid(self):
        assert self.demo.pid

    def test_scan_finish(self):
        # TODO: we should assert something about values or text output here?
        subprocess.check_call(split("python3 -m plom.scan status"), env=self.env)
        r = subprocess.call(split("python3 -m plom.finish status"), env=self.env)
        # TODO: fix up this, seems erratic, perhaps even non-deterministic?
        assert r >= 0  # numScanned - numberComplete
        assert self.demo.process_is_running()

    def test_get_ver_map(self, tmpdir):
        tmpdir = Path(tmpdir)
        from plom.create import download_version_map
        from plom.create import version_map_from_file

        # TODO: use connectmanager messenger, See MR !1275.
        from plom.create import start_messenger

        msgr = start_messenger(
            self.env["PLOM_SERVER"], self.env["PLOM_MANAGER_PASSWORD"], verify_ssl=False
        )
        try:
            qvmap = download_version_map(msgr=msgr)
        finally:
            msgr.closeUser()
            msgr.stop()

        f = tmpdir / "foo.csv"
        subprocess.check_call(
            split(f"python3 -m plom.create get-ver-map {f}"), env=self.env
        )
        assert f.exists()
        qvmap2 = version_map_from_file(f)
        assert qvmap == qvmap2

        f = tmpdir / "foo.json"
        subprocess.check_call(
            split(f"python3 -m plom.create get-ver-map {f}"), env=self.env
        )
        assert f.exists()
        qvmap2 = version_map_from_file(f)
        assert qvmap == qvmap2

    # This test assumes very specific setup of the Lite Demo
    # The test can be updated if those details change.
    def test_prename_predictions(self):
        # TODO: use connectmanager messenger, See MR !1275.
        from plom.create import start_messenger

        msgr = start_messenger(
            self.env["PLOM_SERVER"], self.env["PLOM_MANAGER_PASSWORD"], verify_ssl=False
        )
        try:
            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            assert "1" in predictions, "The lite demo has the first one predicted"
            sid = predictions["1"]["student_id"]
            cert = predictions["1"]["certainty"]
            pred = predictions["1"]["predictor"]
            assert sid == "10050380"
            assert 0.5 < cert < 1
            assert pred == "prename"
            assert "2" not in predictions, "only first one predicted"

            # TODO: did we want this to test for conflict?
            # Issue #2404: maybe we want conflicts for prename but not other predictors?
            # with raises(PlomConflict, match="elsewhere"):
            #     msgr.pre_id_paper(2, sid)

            msgr.remove_pre_id(1)

            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            assert "1" not in predictions

            # now we can assign `sid` to paper 2
            msgr.pre_id_paper(2, sid)
            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            assert "2" in predictions
            assert predictions["2"]["student_id"] == sid

            # now we can assign ANYTHING else to paper 2's prediction
            msgr.pre_id_paper(2, "eleventyfour")
            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            assert "2" in predictions
            assert predictions["2"]["student_id"] == "eleventyfour"

            # we leave the state hopefully as we found it
            msgr.remove_pre_id(2)
            msgr.pre_id_paper(1, sid, predictor="prename")
            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            assert "1" in predictions
            assert "2" not in predictions
            assert predictions["1"]["student_id"] == sid
            assert predictions["1"]["certainty"] == cert
            assert predictions["1"]["predictor"] == pred

        finally:
            msgr.closeUser()
            msgr.stop()

    # This test assumes very specific setup of the Lite Demo
    # The test can be updated if those details change.
    def test_unid(self):
        # TODO: use connectmanager messenger, See MR !1275.
        from plom.create import start_messenger

        msgr = start_messenger(
            self.env["PLOM_SERVER"], self.env["PLOM_MANAGER_PASSWORD"], verify_ssl=False
        )
        try:
            iDict = msgr.getIdentified()
            assert len(iDict) == 0, "Currently no one IDed in the lite demo"

            predictions = msgr.IDgetPredictionsFromPredictor("prename")
            sid = predictions["1"]["student_id"]
            cl = msgr.IDrequestClasslist()
            (person,) = [x for x in cl if x["id"] == sid]
            msgr.id_paper(1, person["id"], person["name"])

            iDict = msgr.getIdentified()
            assert len(iDict) == 1

            # need not be 2, any unID'd paper
            assert "2" not in iDict
            sid, name = iDict["1"]
            assert sid == "10050380"
            assert "Fink" in name
            # paper 2 is not ID'd but we expect an error if we ID it to Fink
            with raises(PlomConflict, match="in use"):
                msgr.id_paper("2", sid, name)
            # not an error to unid the unid'd
            msgr.un_id_paper(2)

            msgr.un_id_paper(1)
            # now paper 1 is unid'd
            iDict = msgr.getIdentified()
            assert "1" not in iDict

            # so now we can ID paper 2 to Iris, then immediately unID it
            msgr.id_paper("2", sid, name)
            msgr.un_id_paper(2)

            # we leave the state hopefully as we found it
            iDict = msgr.getIdentified()
            assert "1" not in iDict
            assert "2" not in iDict
        finally:
            msgr.closeUser()
            msgr.stop()

    def test_random_IDing(self):
        subprocess.check_call(split("python3 -m plom.client.randoIDer"), env=self.env)

    def test_get_rubrics_default_extension_is_toml(self, tmpdir):
        f = Path(tmpdir) / "foo"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        assert f.with_suffix(".toml").exists()

    def test_get_rubrics_toml(self, tmpdir):
        f = Path(tmpdir) / "foo.toml"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        assert f.exists()

    def test_put_rubrics_demo(self, tmpdir):
        subprocess.check_call(
            split("python3 -m plom.create rubric --demo"),
            env=self.env,
        )
        f = Path(tmpdir) / "foo.json"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        with open(f, "r") as fh:
            L = fh.readlines()
        assert any("chain rule" in x for x in L)

    def test_random_grading(self):
        subprocess.check_call(split("python3 -m plom.client.randoMarker"), env=self.env)

    def test_finish_audit(self):
        # TODO: need to save into tmpdir
        subprocess.check_call(split("python3 -m plom.finish audit"), env=self.env)
        f = Path("audit.json")
        assert f.exists()

    def test_scan_finish_after(self):
        subprocess.check_call(split("python3 -m plom.scan status"), env=self.env)
        r = subprocess.call(split("python3 -m plom.finish status"), env=self.env)
        # TODO: fix up this, seems erratic, perhaps even non-deterministic?
        assert r >= 0  # numScanned - numberComplete
        assert self.demo.process_is_running()
