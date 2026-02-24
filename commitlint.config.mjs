/** @type {import('@commitlint/types').UserConfig} */
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
      ],
    ],
    "type-max-length": [2, "always", 15],
    "scope-empty": [0, "never"],
    "scope-min-length": [2, "always", 1],
    "scope-max-length": [2, "always", 20],
    "subject-case": [
      2,
      "never",
      ["sentence-case", "start-case", "pascal-case", "upper-case"],
    ],
    "subject-max-length": [2, "always", 120],
    "header-min-length": [2, "always", 10],
    "header-max-length": [2, "always", 120],
    "body-leading-blank": [2, "always"],
    "body-max-length": [2, "always", Infinity],
    "body-max-line-length": [2, "always", Infinity],
    "footer-leading-blank": [2, "always"],
    "footer-min-length": [2, "always", 0],
    "footer-max-line-length": [2, "always", 120],
  },
  defaultIgnores: true,
  helpUrl: "https://github.com/conventional-changelog/commitlint",
  prompt: {
    messages: {
      skip: ":skip",
      max: "upper %d chars",
      min: "%d chars at least",
      emptyWarning: "can not be empty",
      upperLimitWarning: "over limit",
      lowerLimitWarning: "below limit",
    },
    questions: {
      type: {
        description: "Select the type of change that you're committing:",
        enum: {
          feat: {
            description: "A new feature",
            title: "Features",
          },
          fix: {
            description: "A bug fix",
            title: "Bug Fixes",
          },
          docs: {
            description: "Documentation only changes",
            title: "Documentation",
          },
          style: {
            description:
              "Changes that do not affect the meaning of the code (white-space, formatting, etc)",
            title: "Styles",
          },
          refactor: {
            description: "A code change that neither fixes a bug nor adds a feature",
            title: "Code Refactoring",
          },
          perf: {
            description: "A code change that improves performance",
            title: "Performance Improvements",
          },
          test: {
            description: "Adding missing tests or correcting existing tests",
            title: "Tests",
          },
          build: {
            description: "Changes that affect the build system or external dependencies",
            title: "Builds",
          },
          ci: {
            description: "Changes to CI configuration files and scripts",
            title: "Continuous Integrations",
          },
          chore: {
            description: "Other changes that don't modify src or test files",
            title: "Chores",
          },
          revert: {
            description: "Reverts a previous commit",
            title: "Reverts",
          },
        },
      },
      scope: {
        description:
          "What is the scope of this change (e.g. component or file name) (optional)",
      },
      subject: {
        description: "Write a short, imperative tense description of the change (lowercase)",
      },
      body: {
        description: "Provide a longer description of the change (optional)",
      },
      isBreaking: {
        description: "Are there any breaking changes?",
      },
      breakingBody: {
        description:
          "A BREAKING CHANGE commit requires a body. Please enter a longer description of the commit itself",
      },
      breaking: {
        description: "Describe the breaking changes",
      },
      isIssueAffected: {
        description: "Does this change affect any open issues?",
      },
      issuesBody: {
        description:
          "If issues are closed, the commit requires a body. Please enter a longer description of the commit itself",
      },
      issues: {
        description: 'Add issue references (e.g. "fix #123", "re #123".)',
      },
    },
  },
};
