# Updates and removal

[简体中文](../zh-CN/updating.md)

Give your Agent the complete target-release artifact and ask:

> Follow INSTALL.md in this artifact to update dasen-skills for the current project. Check the current version and local edits, preserve the old release and articles, prepare the new environment, switch the project, and verify the version actually loaded.

Registered hosts in this project switch together; other projects keep their versions. Preserve conflicting user changes and explain how to resolve them.

To roll back, ask the Agent to rebind the previous release using its ready receipt under INSTALL.md. Version rollback does not restore article or configuration backups.

To remove, ask it to remove this project's Dasen-owned entries while preserving articles and shared environments. Shared payloads and runtimes are not automatically deleted.

A moved project or new computer needs rebinding and verification; copying a virtual environment is insufficient. See [INSTALL.md](../../INSTALL.md) for operational details.
