# Plom Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
* preliminary support for a canned user list.
* autogenerate password suggestions for new users.

### Changed
* make 04 script less verbose.

### Fixed
* userManager was failing to start.
* return to greeter dialog on e.g., wrong server or pagegroup/version out of range.


## [0.2.0] - 2019-10-11

### Added

#### Client
* delete tool: right-mouse button drag sweeps out a rectangle and deletes its contents.
* improve zoom ("ctrl-=" cycles through zoom modes)
* shift-click and control-click should now emulate right-click and middle-click.
* middle-button in line/pen tools creates line/path with arrow-heads at both ends.
* annotations are now saved in ".plom" files, supports continuing previously marked papers.
* marker now uploads/downloads papers in the background.

#### Server
* Handle upload/download of .plom files.
* New `12_archive` script makes a minimal zip file for archiving.
* Support for Docker.
* New templates for making your own tests.

### Changed

#### Client
* client not backward compatible with v0.1.0 servers.
* mark-total mode is removed.
* comment-delta is now its own grouped object, with many changes to encourage comment-reuse.
* comment-add and edit is now via a pop-up window.
* user can now make 0-point comments (for which the zero is pasted).
* user can also make no-point comments which are pasted as just text.
* general GUI improvements

#### Server
* Server not backward compatible with v0.1.0 clients.
* More general support for student names.
* Returned PDF files have better sizes for printing hardcopies

### Fixed

* Many many bugfixes.


## 0.1.0 - 2019-06-26

This is the first release of Plom, PaperLessOpenMarking.


[Unreleased]: https://gitlab.math.ubc.ca/andrewr/MLP/compare/v0.2.0...master
[0.2.0]: https://gitlab.math.ubc.ca/andrewr/MLP/compare/v0.1.0...v0.2.0
