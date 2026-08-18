import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bash_effect as be


class TestClassify(unittest.TestCase):
    def test_read_only_commands(self):
        for cmd in ["ls -la", "cat notes.md", "grep -rn foo .", "git status",
                    "git log --oneline", "git diff HEAD", "wc -l f.txt",
                    "find . -name '*.py'", "gh api repos/x/y"]:
            self.assertEqual(be.classify(cmd), "read_only", cmd)

    def test_redirect_to_devnull_is_not_a_write(self):
        self.assertEqual(be.classify("grep foo bar.txt 2>/dev/null"), "read_only")
        self.assertEqual(be.classify("make 2>&1 >/dev/null"), "read_only")

    def test_writing_commands(self):
        for cmd in ["cat > notes.md <<'EOF'", "echo hi > f.txt", "touch f",
                    "mkdir -p a/b", "sed -i '' 's/a/b/' f.txt", "tee out.log",
                    "cp a b", "echo x >> log.txt"]:
            self.assertEqual(be.classify(cmd), "writing", cmd)

    def test_destructive_commands(self):
        for cmd in ["rm -rf build", "git push origin main", "git push --force",
                    "git reset --hard HEAD~1", "git rebase -i main",
                    "git filter-repo --path x", "git branch -D feat",
                    "gh api -X DELETE repos/x/y", "gh repo delete x",
                    "mv important.db backup.db"]:
            self.assertEqual(be.classify(cmd), "destructive", cmd)

    def test_git_add_and_commit_are_writing_not_destructive(self):
        self.assertEqual(be.classify("git add -A"), "writing")
        self.assertEqual(be.classify("git commit -m 'x'"), "writing")

    def test_empty_and_none(self):
        self.assertEqual(be.classify(""), "read_only")
        self.assertEqual(be.classify(None), "read_only")

    def test_compound_takes_the_strongest_effect(self):
        self.assertEqual(be.classify("ls && rm -rf build"), "destructive")
        self.assertEqual(be.classify("git status && echo x > f"), "writing")

    def test_is_state_changing(self):
        self.assertTrue(be.is_state_changing("echo x > f"))
        self.assertTrue(be.is_state_changing("rm f"))
        self.assertFalse(be.is_state_changing("cat f"))


if __name__ == "__main__":
    unittest.main()
