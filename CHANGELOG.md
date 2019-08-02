# PLOM Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Client
Annotator:
* right-mouse button (or now shift-click) with delete tool sweeps out a rectangle and deletes its contents.
* "ctrl-=" cycles through zooms (user, fit-width, fit-height). Also added this shortcut to the key-help list.
* comment-delta is now its own grouped object. The text cannot be edited in situ, it must be edited in the comment-list. This is deliberate to (hopefully) encourage comment-reuse.
* comment-add and edit is now via a pop-up window (rather than in-place in the list). The user can enter a new comment or select text from the current page via the combo-box.
* shift-click and control-click should now emulate right-click and middle-click in annotation.
* middle-button (or ctrl-click) in line/pen tools creates line/path with arrow-heads at both ends.
* Annotator can save / load ".plom" files and so "pickle" the graphical objects on the page. This function is handled by the marker-window not the annotator window (see below).
* When mark-total, the comment-delta's are suppressed and will not be pasted into the page.

Marker:
* Annotated papers are now "pickled" as ".plom" files - these are kept locally and also uploaded to server.
* Consequently no longer compatible with v0.1.0
* User can now select an already marked paper (either from this instance or earlier marking) and select "annotate". They will be prompted by a "Do you want to keep editing" window. If "yes" then the annotator is fired-up and "unpickles" the required graphical objects so that the user can continue editing where they left off.
* Marker now uploads/downloads papers in the background. User should notice speedup but (hopefully) not much else.

#### Server
* New server needed to handle upload/download of plom files. Not backward compatible with v0.1.0

### Changed

### Fixed


## 0.1.0 - 2019-06-26

This is the first release of PLOM, PaperLessOpenMarking.


[Unreleased]: https://gitlab.math.ubc.ca/andrewr/MLP/compare/v0.1.0...master
