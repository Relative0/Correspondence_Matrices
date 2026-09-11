# Repository-specific GitHub authentication

Git publication for this project uses the stored `Relative0` account through Git Credential Manager. The GitHub CLI may remain signed in to another account for other projects. No global account switch, logout, token copying or credential clearing is needed.

For this checkout, the remote is `https://Relative0@github.com/Relative0/Correspondence_Matrices.git`. The local `credential.https://github.com.helper` list first resets inherited helpers and then selects `manager`. These settings are local machine configuration and are not embedded in the repository or website.

A GitHub CLI permission failure under another account does not establish that this repository's Git credential lacks write access. Use the repository's credential binding for Git pushes, and verify the resulting Pages deployment and live file checksums. A dry-run is a preflight, not a publication receipt.

When creating another release checkout, configure its remote account and local helper too; those settings are not inherited from this checkout. Do not replace another project's account configuration or copy tokens into files or environment variables.

Reference: [Git Credential Manager: multiple users](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/multiple-users.md).
