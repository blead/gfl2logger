import re
import unittest
from pathlib import Path

from gfl2logger.utils.version import VERSION

TAG = f"v{VERSION}"
ASSETS = (
    f"gfl2logger-{TAG}-windows-x64.zip",
    f"gfl2logger-{TAG}-macos-arm64.dmg",
    f"gfl2logger-{TAG}-macos-arm64.zip",
)


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


class ReleaseConsistencyTests(unittest.TestCase):
    def test_documents_link_every_asset_of_the_current_version(self) -> None:
        for document in ("README.md", "README_KR.md", "RELEASE_NOTES.md"):
            text = read(document)
            for asset in ASSETS:
                with self.subTest(document=document, asset=asset):
                    self.assertIn(
                        f"(../../releases/download/{TAG}/{asset})",
                        text,
                    )

    def test_documents_do_not_link_assets_of_other_versions(self) -> None:
        for document in ("README.md", "README_KR.md", "RELEASE_NOTES.md"):
            linked = set(re.findall(r"releases/download/(v[\d.]+)/", read(document)))
            with self.subTest(document=document):
                self.assertEqual(linked, {TAG})

    def test_release_notes_are_for_the_current_version(self) -> None:
        self.assertTrue(read("RELEASE_NOTES.md").startswith(f"# gfl2logger {TAG}\n"))

    def test_workflows_build_the_documented_asset_names(self) -> None:
        build = read(".github/workflows/build.yml")
        release = read(".github/workflows/release.yml")
        for asset in ASSETS:
            suffix = asset.removeprefix(f"gfl2logger-{TAG}")
            with self.subTest(asset=asset):
                self.assertIn(f"gfl2logger-${{VERSION_LABEL}}{suffix}", build)
                self.assertIn(
                    f"gfl2logger-${{{{ github.ref_name }}}}{suffix}", release
                )

    def test_workflow_expressions_never_reach_a_shell_script(self) -> None:
        # Values such as the tag name are passed through inputs and environment
        # variables; expanding ${{ }} inside a run script would allow injection.
        allowed = (
            "runs-on:",
            "name:",
            "tag_name:",
            "version-label:",
            "VERSION_LABEL:",
            "group:",
            "release/gfl2logger-",
        )
        for workflow in ("build.yml", "ci.yml", "release.yml"):
            for line in read(f".github/workflows/{workflow}").splitlines():
                if "${{" in line:
                    with self.subTest(workflow=workflow, line=line.strip()):
                        self.assertTrue(line.strip().startswith(allowed))

    def test_both_platforms_are_built_from_one_product_name(self) -> None:
        spec = read("gfl2logger.spec")
        self.assertNotIn("gf2logger'", spec.replace("org.gf2logger.app", ""))
        self.assertIn("name='gfl2logger.app'", spec)

        build = read(".github/workflows/build.yml")
        self.assertIn("windows-latest", build)
        self.assertIn("macos-15", build)

    def test_windows_is_not_built_as_a_self_extracting_single_file(self) -> None:
        # The WinDivert driver stays loaded from the program's own files; a single-file
        # build could never remove its temporary directory on exit.
        spec = read("gfl2logger.spec")
        self.assertEqual(spec.count("exclude_binaries=True"), 2)
        self.assertEqual(spec.count("COLLECT("), 2)


if __name__ == "__main__":
    unittest.main()
