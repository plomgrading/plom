# Plom Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.15.6] - 2024-07-30

### Added
* Client: in experimental mode, add an on-page menu for manipulations such as rotating, reordered and removing.
* Client can spell check rubrics.
* Client can query for a list of other papers that used a particular rubric and display those annotations to the user.
* Tasks can be reassigned between users on the server.
* Questions can be tagged with, for example, learning objectives.
* The revision history of rubrics is stored and viewable.

### Changed
* Assessments with an odd number of pages now generate errors, which seems like a major change but has always been our best-practice.
* Client: improvements to the undo stack.
* Its easier to wipe the new server back to its initial empty state, at least before scanning begins.
* Minor tools in annotator are reordered to put tick first and box later.

### Fixed
* Client: line widths scale with annotation scale.
* Better classlist validation when prenaming.
* Continued implementation of the new server.
* Misc fixes and improvements.
* legacy-server: minor fixes to legacy workflow.


## [0.15.5] - 2024-06-12

### Added
* Users can change their own passwords.

### Changed
* Plom now allows sharing pages between questions.
* Client: parameterized rubrics are no longer considered experimental.

### Fixed
* For now, you must manually create system rubrics before marking begins; to enforce this the client will crash if the server has no rubrics.
* Misc fixes and documentation improvements.
* Spec verifier now checks that numberOfPages is even.


## [0.15.4] - 2024-05-21

### Added
* Scanning (on the new server) defaults to automatic image extraction (if its detected safe to do so).  Scanners can force "safe mode rendering" for the previous behaviour.

### Changed
* Plom is less aggressive about "font subsetting" when creating PDF files which might make generated PDFs a little bit safer.

### Fixed
* Workaround spurious characters appearing on generated pages when using certain versions of PyMuPDF.


## [0.15.3] - 2024-05-11

### Added
* Server can now show and in some cases customize the feedback rules that nag clients before they submit annotations.
* New feedback rule checks that each page is annotated.

### Changed
* Rubrics now keep more careful records about who modified them and when.

### Fixed
* Legacy workflow: `plom-scan upload ./foo.pdf` will now explicitly fail informing you to keep path info out of bundle names.
* Processing PDF scans: don't complain about rounding errors when instead some metadata mixup about width/height has occurred.
* Client: clicking "sync" to synchronous rubrics from server no longer resets selection.


## [0.15.2] - 2024-03-11

### Added
* Server - scanner can now bulk-discard unknown pages from a bundle, and bulk change discards back to unknowns.
* Server: supports tags in more places.

### Changed
* Client respects Question Labels in more places.
* Server container should automatically hotstart if a database exist.  Previously behaviour was to delete and start again.
* Experimental support for users to modify each others' rubrics.
* Server: new settings to control global create/modify rubric permissions.

### Fixed
* Legacy server: fix crash when client asks to view images from paper which exists but has no scans.
* Server: fix crash when client asks for non-existing Annotation images.
* Client: popup error message when viewing non-existent images rather than empty blue dialog.
* Client: fix a crash on sync when rubric's per-version was changed.


## [0.15.1] - 2024-02-16

### Added
* Django-based server container starts the canned demo if environment variable `PLOM_DEMO` is set to 1.

### Changed
* Web UI: displays version number.
* Web UI: various tweaks and improvements to building blank paper PDFs.
* `plom-manager` command is deprecated; use `plom-legacy-manager` to manage legacy servers.

### Fixed
* Web UI: improved error handling for unexpected errors when using asynchronous HTMX calls.


## [0.15.0] - 2024-02-13

### Added
* Django-based server is closer to being the default server.

### Changed
* switch client dependency from `appdirs` to `platformdirs`.

### Fixed
* `-1` as papernum wasn't worked for input classlists.


## [0.14.8] - 2024-01-04

### Added
* Identifier: UI includes explanation of why we confirm prenamed papers.

### Changed
* The "new" `idBox3.pdf` was giving warnings in LaTeX: new `idBox4.pdf` is now a 1.5 PDF.
* Client: experimental "view cat pic" feature removed; it was often offline and the content could be construed as endorsed by Plom.

### Fixed
* Client: temporary workaround for Qt bug resulting in overly-long error dialogs on macOS.
* Previous compiled clients `0.14.x` produced imperceptibly corrupted annotated images due to bugs in jpeg libraries, causing rare problems with some PDF viewers on the reassembled files.
* Client: crash when sorted columns in the rarely-used "filter/arrange" dialog.
* Dependency and documentation updates.


## [0.14.7] - 2023-12-03

### Added
* Support for Python 3.12.

### Changed
* Clients: more dialogs have "Don't ask me again" checkboxes.
* "Don't ask me again" settings are stored only in the current session (for now).
* Don't show default "1" paper and page when assigning unknown pages.

### Fixed
* Duplicated paper numbers in question-version map input will now be detected.
* Correctly handle solutions that encode to jpeg.
* Fix some version clashes between old pyOpenSSL and cryptography by forcing users to update both.
* Legacy server: increase json upload limit to 5MiB to accept larger question-version maps.


## [0.14.6] - 2023-11-02

### Changed
* Improved messages for push-to-canvas script.

### Fixed
* Fix crash in Manager viewing annotations in Review tab.
* Documentation and misc fixes.


## [0.14.5] - 2023-10-23

### Added
* New "idBox3.pdf" template moves the signature box up to avoid signatures hitting the bounding box (which was leading to additional manual IDing).
* Page Arrange: new "Invert selection" button is useful to quickly discard all but the highlighted pages.

### Changed
* Do more checks before uploading a custom version map, hopefully avoiding errors that are hard to recover from.
* Making self-signed certs no longer needs command-line `openssl`, instead uses the `cryptography` package.

### Fixed
* Wrong padding on the top paper number box on recent versions of PyMuPDF.
* Various fixes for Python 3.12 but full support may be waiting on a new release of AIOHttp library.
* Fix a crash in server manager when unpredicting a row without a prediction.
* Improved contrast in Identifier client when OS is in dark mode.
* Push-to-Canvas could fail when assessment shortname contained underscores.
* Documentation edits and fixes.


## [0.14.4] - 2023-10-10

### Changed
* Various edits to contrib scripts, especially pulling from Canvas.

### Fixed
* Fix a crash when users sync a changed rubric.
* Clearer error messages when auto-IDing an a student number has less than 8 digits.
* Filter leading/trailing whitespace from server address.
* Fixes in contrib scripts related to just-in-time prenaming and IDing.
* Typos and clarifications in docs.


## [0.14.3] - 2023-09-15

### Fixed
* Fix crash on start of the provided macOS client binaries.
* Manager can login to Client before the server has a spec.


## [0.14.2] - 2023-09-13

### Added
* Absolute rubrics are no longer considered experimental and can be created in the Add
  Rubric dialog by default.

### Changed
* The legacy `sidToTest` API call (rarely used) now reports whether the paper is IDed
  or prenamed.  This is documented in `msgr.sid_to_paper_number()`.
* Many next-gen server changes.

### Fixed
* Client: crash from invalid version restrictions specified in the Add Rubric dialog.
* Legacy server was not creating backup files on regrade since sometime in 2022.
* Fix regrading on next-gen servers.
* Client: rubric tabs now hide properly when all rubrics inside them are hidden.


## [0.14.1] - 2023-09-01

### Added
* The next-gen web-based Plom Server is ready for wider testing.  Production use should probably remain on the "Legacy Plom Server" for the time being.
* Plom Client can connect to both the next-gen server and the legacy server.
* Plom Client supports `http://` URLs, if specified explicitly, e.g., for development.  The default remains `https://`

### Changed
* On the next-gen server, papers can be graded in a random but predetermined order.
* On the next-gen server, the priority for papers to be graded can be changed.
* Plom now requires at least Python 3.8.

### Fixed
* Shared "group tabs" can now be re-ordered on a per-user basis.
* Crash fixes when multiple clients are tagging.


## [0.13.3] - 2023-04-25

### Changed
* Client: when a rubric group tab is selected, adding a new rubric defaults to that group.
* Manager: the Dangling Pages tab must be manually refreshed.

### Fixed
* Manager: no longer checks for "Dangling Pages" on start-up b/c this was very slow on large servers.


## [0.13.2] - 2023-04-03

### Changed
* Client: "sync" button doesn't pop up a dialog unless there are changes to rubrics.
* Client: "sync" button shows "diffs" of changes to rubrics.
* Non-user-facing changes to how images and image metadata is handled.

### Fixed
* Client: "sync" button was not indicating changes made to existing rubrics.
* Manager: partial fix (no more crash) when trying to create synthetic substitute ID pages.
* Client: clicking "cancel" in options dialog no longer applies the options anyway.
* Misc UI fixes.


## [0.13.1] - 2023-02-24

### Changed
* Cover pages of returned work now include the "long name" of the exam.

### Fixed
* Manager: assigning papers to "reviewer" was broken server-side (older clients should work with 0.13.1 server).
* Manager: re-assembling papers works again in distributed binaries on Windows and macOS platforms.
* Rubrics should render correctly in dialogs, even if they contain HTML.
* Misc UI fixes.


## [0.13.0] - 2023-02-13

### Fixed
* Ensure Client <= 0.12.2 cannot connect to servers, ensures client bug #2521 (fixed in 0.12.3) cannot mismatch IDs.
* Misc UI fixes.


## [0.12.3] - 2023-02-11

### Changed
* Rubrics: suggest new group name from existing, e.g., have (a), (b) then suggest (c).
* Client: prevent lots of new tabs, which fills the tab bar and could be confusing.

### Fixed
* Identifier client bug #2521: "Accept Prediction" button now saves the correct student ID.
* Group names must not have spaces, but client no longer crashes if you make one.
* Remove empty tab on removal of last rubric from group.
* Only "custom user tabs" can be renamed: fix context menus to reflect this.
* Misc fixes.


## [0.12.2] - 2023-02-05

### Changed
* Identifier displays more meaningful certainty values for the Assignment Problem predictions.

### Fixed
* Fixed a crash when explicitly syncing rubrics.
* "Experimental features" is now persistent during a single session.


## [0.12.1] - 2023-01-27

### Added
* `plom-create` command line tool can list and clear paper id prediction tables.
* Plom-Client has an "experimental" menu item: currently creates a bit of friction before using the new parameterized rubrics and absolute rubrics.

### Changed
* Revamp Chooser dialog, add "about" dialog.
* Add "about" dialog and version info to Manager tool.
* Possible (if somewhat ill-advised) to replace the prenaming after papers have been created.
* Sadly, the "cat break" feature is currently disabled as the external service is not currently reliable.

### Fixed
* Fix rendering of parameterized rubrics.
* Fix modifying group of initially non-grouped rubrics.
* Add notice to UI that macOS packaged binaries cannot reassemble, link to issue.
* Misc fixes.


## [0.12.0] - 2023-01-21

### Added
* "Tech preview" of a web-interface for configuring a Plom server.
* Users can create "absolute rubrics" of the form "2 of 3: comment".
* The "scope" of rubrics can be adjusted:
    - Rubrics can be version-specific.
    - Rubrics can be parameterized using per-version textual substitutions.
    - Rubrics can be organized into groups such as "(a)" which correspond to
      shared tabs.
    - Rubrics can be made "exclusive" within a group: at most one rubric can
      be used from each exclusive group.
* Manager can "bulk-forgive" missing do-not-mark pages.
* Support for external databases.

### Changed
* Server stores annotation data in the database instead of in `.plom` files.
* Client no longer has a "No Answer" button: instead use the "no answer given" rubric.
* Support for non-ascii names is much improved.
* Client: simulated slow network mode for testing/debugging.
* Manager sorts unknown pages by their position in the bundle.

### Fixed
* Client: fix potential UI crashes when grading is complete.
* Longer question labels are possible.
* Long names can fit on the prenamed pages by auto-shrinking font.
* Output of `plom-finish status` is easier to understand.
* Misc fixes.


## [0.11.1] - 2022-11-14

### Added
* Documentation improvements.

### Changed
* Client "Tips" screen has more information.
* Command line tools document the available environment variables.
* `plom-scan` and `plom-hwscan` now invisibly watermark PNG/JPEG files, making unique images from identical pages (#1573).

### Fixed
* Fix a client-side crash on unexpected identical images (same hash) within the same paper (#2331 and others).
* Fix a manager crash when reassembling and current working directory is not writable (#2335).
* Misc bug fixes and fixes for potential table sorting issues.


## [0.11.0] - 2022-09-24

### Changed
* classlist upload can be forced, allowing one to overwrite the server's classlist.

### Fixed
* Various other fixes.


## [0.10.1] - 2022-09-08

### Added
* manager: faster keyboard navigation of the Unknown Pages dialog.
* re-enable the "review" feature.

### Changed
* `plom-create newspec` replaces `plom-create new` (although both work).
* `plom-create validatespec` replaces the previously deprecated `plom-create parse`.
* manager: respects question labels in most places.

### Fixed
* Fix macOS and Windows compiled clients crashes due to missing keyboard maps.
* Fix errors about non-unique rubric keys during server init.
* Various other fixes around server init.


## [0.10.0] - 2022-08-22

### Added
* Annotator: help dialog shows diagrams for keyboard shortcuts.
* Annotator: help dialog shows some "getting started" info for click-drag.
* Marker: can prefer papers tagged `@user`.
* Marker: can start marking at a particular paper number.

### Changed
* Spec format has changed: `[[question]]` is now preferred to `[question.1]` (for now both are supported).
* QR format changed, future proofing for more papers, versions and pages.
* "Public Code" shortened from 6 digits to 5.
* Closing Annotator now resets the current tool.
* Annotator: some shortcut keys are now changeable in the help dialog, but this feature is still "beta".

### Fixed
* Some slow bottleneck API calls are faster, although more work is needed.
* Annotator: shortcut keys should display correctly on macOS.
* Annotator: keybindings are now saved between sessions (except for Custom mappings)
* Annotator: many small UI fixes.
* Various documentation fixes.


## [0.9.4] - 2022-08-04

### Fixed
* Fix various Manager UI paper creation functions when using precompiled binaries.
* Fix several Manager UI crashes.


## [0.9.3] - 2022-07-18

### Added
* `plom-create` can manipulate tags.
* Can tag while peeking at previously marked papers.

### Fixed
* Fixes on Python 3.7, and improved CI to ensure minimum Python is tested.
* Fix build of papers with DMN on higher pages such as page 16.
* Annotator: potentially less flaky PageScene due to many bug fixes.
* Fix duplicated LaTeX error dialog.
* LaTeX bounding box size fixes on modern systems.
* Code and dependency cleanups, removal of deprecated code.


## [0.9.2] - 2022-06-14

### Added
* Manager UI tool can add spec and build papers, and download the `marks.csv`.

### Fixed
* Client: creating and modifying tabs is more obvious with context menus and `+` button.
* Client Identifier zoom level is against persistent between papers (as in 0.8.x).
* UI and other fixes.


## [0.9.0] - 2022-05-25

### Added
* `plom-server` will autogenerate a manager password if it is started without one.
* `plom-create` can manage user accounts of a running server.
* Manager displays bundle name/page of unknown pages.
* `plom-scan status` now displays information about bundles and unknown pages.
* `plom-finish audit` produces a JSON file for post-grading checking/followup/etc
* Annotator now has a crop tool (in menu) that allows user to excluded unwanted parts of page.
* Annotator now has a "view previous" function that pops up a window that will show previously marked paper(s).
* Clients can use ctrl-mousewheel to zoom in and out.
* Manager: can tag questions and remove annotations, in bulk.
* Demos and testing: randoMarker now also tags random selection of tasks.

### Changed
* Plom now requires Python 3.7.
* Plom no longer supports older macOS 10.13 as we cannot reliably build binaries on that system.
* `plom-create` DB creation now done one test at a time which avoids timeouts and enables future flexibility.
* Manager: improvements to the prediction-related UI.
* Classlists that are not from Canvas must now include a `paper_number` column, which can be left blank.
* The Plom test-spec no longer uses `numberToName`, instead use the "paper_number" column in the classlist.
* Reassembled files are now time-stamped.
* It is easier to insert extra pages during marking and fewer annotations are wiped (only those in the question directly effected).
* Manager: improved interface around IDing and predictions.
* Manager: improved control of the automatic ID reader.
* Prenamed papers and machine ID reading are in flux: currently both need to be confirmed by a human in the Identifier client.  Expect further future changes.
* Many API changes and tweaks.

### Fixed
* Non-zero initial orientations should now work properly.
* Custom solutions had the wrong coverpage, showing instead the reassembled coverpage.
* Rapid use of the Ctrl-R dialog no longer needs to wait on the background downloader.
* Improved and hopefully less crashing in classlist validation.
* Timezones are now made explicit.
* Many UI fixes and tweaks.
* Ongoing documentation improvements.
* Many other fixes.


## [0.8.11] - 2022-04-12

### Fixed
* For now, only manager can change passwords.
* Slow client during Rearrange Page dialog use immediately on new page should be fixed.


## [0.8.10] - 2022-03-27

### Added
* plom-create subcommand "status" reports server status.

### Changed
* We cannot no longer reliably build for macOS 10.13, will do so on a "best effort" basis.  Users should upgrade to at least macOS 10.14.

### Fixed
* Don't pop up a spurious warning about duplicated pages when scanned data had duplicates.
* Shorten overly long page name lists in Rearrange Pages dialog.
* Build fixes on older macOS releases.
* Minor bug fixes.


## [0.8.8] - 2022-03-14

### Added
* Manager shows totals and highlights tabs that need attention.
* Add word "Test" to paper label: "Test 0123 Q1  p. 4".
* Version numbers to Canvas-related scripts.

### Fixed
* Manager tool was broken on Windows.
* Misc fixes and code cleanups.


## [0.8.7] - 2022-03-02

### Added
* ``plom-create get-ver-map`` command to extract the version map from a running server.
* Canvas utilities can now take student lists from Sections not just Courses.

### Fixed
* Fixed double-undoing during drag-box creation.
* Fixes in Canvas utilities.
* Various other fixes.


## [0.8.6] - 2022-02-13

### Fixed
* "UnID" feature of manager was broken.
* Other minor fixes.


## [0.8.5] - 2022-02-11

### Changed
* Increase read default read timeouts.
* Clean up demo scripts.


## [0.8.2] - 2022-02-07

### Fixed
* Fix broken Windows client binary.
* Fix few contrib scripts.
* Fixed mockplom LaTeX style (for mocking up Plom's QR codes) on recent systems (which sadly breaks it on TexLive 2019 and earlier).
* Misc fixes.


## [0.8.1] - 2022-02-03

### Changed
* Unknowns can be mapped to multiple HW Pages.

### Fixed
* Fix demos when used with invalid SSL certs.
* Misc fixes.


## [0.8.0] - 2022-02-01

### Added
* Manager can "unidentify" papers including prenamed papers.
* Solutions - can now optionally watermark solutions with the SID.
* SSL verification enabled by default for releases.
* Extra pages can optionally map onto more than one question.
* Client Marker window can request any paper number with a long press on "Get next".
* Mild warnings when user gives 0 but there are some ticks on page. Similar mild warnings when user gives full but there are crosses.
* Manager and plom-finish now has list of "dangling" pages - ones which are attached to not-completely-scanned groups. Manager can remove those pages.
* GNU/Linux binaries now using AppImage which should be more portable.
* More sanity checks especially around finishing and uploading.

### Changed
* Command line tool `plom-build` has been renamed to `plom-create` and/or `python3 -m plom.create`.
* Module `plom.produce` has been renamed to `plom.create`.
* Tags have been overhauled, with bug fixes and improved functionality
* Annotator can tag papers directly.
* Server can now optionally start without a spec file.
* Deprecated "LoosePages" have been removed.
* Tests have exactly one ID page (before they could have more than one).
* Spec files have more sanity checks and some keys are now optional.
   - Do not mark pages now specified directly as list "doNotMarkPages = [1,2,3]"
* Misc plom-manager improvements.
* API calls have a default 10s timeout (and 2 retries), so semi-inevitable failures fail faster.
* Top-middle "stamp" on pages now shows the group label (question number, DNM, etc)
   - and extra sheet templates have been updated to match.
* Work in progress on updating annotation styles.
* The history of connections between rubrics is tracked in their metadata.

### Fixed
* Potential memory leaks in Annotator, Manager, and dialogs.
* JPEG support is no longer restricted to sizes in multiples of 16, better rotation support.
* Improved disc-space usage due to JPEG use in more places.
* Removing or adding pages is more selective about which annotations are invalidated.
* A large number of modal dialog fixes.
* Other misc changes.


## [0.7.12] - 2022-01-30

### Fixed
* Minor fixes.


## [0.7.11] - 2021-12-22

### Changed
* Client warns if its version is older than the server.

### Fixed
* Classlist import was broken when using multiple name fields.
* MacOS continuous integration fixed.
* Fix a crash in autoIDing related to unhandled errors.


## [0.7.9] - 2021-12-06

### Added
* Manager can "unidentify" papers including prenamed papers.
* Horizontal position of the prenamed box can be tweaked from command line.

### Fixed
* Client: save user tabs on manual sync and on annotator close.
* Workarounds for high memory use during reassembly and solution assembly.
* Correctly stop background uploader thread on Marker close.
* Client: refreshing solution view updates image from server.


## [0.7.7] - 2021-11-15

### Changed
* Client: fit-to-width and fit-to-height pan to the top and left respectively.

### Fixed
* Tweaks and fixes about reassembly and solution assembly.
* Client: better dark theme support, other tweaks.
* Other minor fixes, including potential crashes caught by `pylint`.


## [0.7.5] - 2021-11-07

### Fixed
* Upload queue length was misreported, potentially losing the last upload on rapid quit.
* Cleanup of client shutdown, hopefully fewer crashes in corner cases.
* Some database cleanup when pages are added to already annotated papers.
* Other minor fixes about admissible usernames and passwords.


## [0.7.4] - 2021-10-28

### Added
* The question-version map can be passed into `plom-build` instead of building a random map.

### Changed
* Image download and reassembly is now interleaved instead of pre-downloading all images.
* Can reassemble just one paper or just one solution.

### Fixed
* Ensure the margin box surrounding the page cannot be deleted.


## [0.7.3] - 2021-10-23

### Changed
* Marker -> View is now allowed to view any question, any paper.

### Fixed
* Clients can tag unannotated questions.
* Various fixes to auto reading of student IDs.
* Various fixes in generating and posting solutions.


## [0.7.2] - 2021-10-13

### Added
* Solutions can be attached to each question/version.

    - client can view solution for the current question/version.
    - solutions for individual students can be returned along with marked test via webpage


### Changed
* plom-scan and plom-hwscan can now list bundles.
* Added a --no-scan option to plom-demo and plom-hwdemo so that fake-data created but not processed or uploaded.
* More import and module improvements: one can now do `python -m plom.client` and `python -m plom.server`, and similarly for most other modules.

### Fixed
* Various CI cleanups that should help external contributors.
* Fixed a crash in the page re-arranger dialog.
* Various other fixes.


## [0.7.1] - 2021-09-23

### Added
* Client binaries for macOS are now distributed as standard .app bundles (still unsigned unfortunately).
* `plom-build make` can now tweak the vertical position of the pre-printed name/ids.
* `plom-build make` can build single papers.
* The server manager UI is now accessible from PlomClient: just login with the manager account.

### Changed
* Classlists can contain additional columns.
* Classlist-related API updates.
* Ongoing improvements to scripting Plom via import and module improvements.

### Fixed
* Papers can be re-printed (without repopulating the database).
* Misc fixes.


## [0.7.0] - 2021-09-04

### Added
* `plom-server launch foo` starts a plom server in the directory `foo`.
* `plom-server` has new command line args to control logging.
* New `PlomServer`, `PlomDemoServer`, and `PlomLiteDemoServer` objects for interactively running servers, or otherwise running a server in a background process.
* `plom-hwscan` can now specify precise per-page mappings from the bundle to questions on the server.
* `plom-hwscan` can override the bundle name.
* LaTeX errors are now displayed to markers.
* `plom-build rubrics` now supports csv in addition to json and toml.

### Changed
* `plom-server launch --mastertoken aabbccdd...` replaces the old way (without the keyword argument).
* QR creation now uses `segno` instead of `pyqrcode`.
* `plom-hwscan` is more flexible about filenames: you do not need to put PDF files in a special directory.
* The `plomgrading/server` container (Docker image) is now based on Ubuntu 20.04.

### Fixed
* `plom-finish reassemble` not longer needs direct file access to the server (except when using the `--ided-only` option).
* Low-level API changes and improvements.
* Many bug fixes.


## [0.6.5] - 2021-07-19

### Changed
* The `jpegtran-cffi` package which is used for lossless jpeg rotations is not longer a hard dependency.  Jpeg is still only used rarely and improvements to the client means its not a serious problem if a few pages are rotated.

### Fixed
* Client: better handling of rare upload failures: warning dialog pops up if the queue is growing, and a single timeout will no longer block the entire queue.
* Misc bug fixes and doc updates.


## [0.6.4] - 2021-06-23

### Added
* Experimental support for writing graded papers and final marks to Canvas.

### Changed
* The `userListRaw.csv` file is no longer inside the serverConfiguration directory.
* Server saves its log to a file automatically (as well as echoing to stdout).

### Fixed
* Misc bug fixes.


## [0.6.3] - 2021-05-28

### Fixed
* Minor bug fix to stop user being able to create 0-point relative rubrics. Related server-side rubric sanity checking.
* Fix Flatpak and source packaging to include icons and cursors.
* Misc bug fixes.


## [0.6.2] - 2021-05-16

### Changed
* Packaging fixes including a revamp of `.../share/plom`.

### Fixed
* Workaround for blurry results from very tall scans.
* Misc bug and documentation fixes.


## [0.6.1] - 2021-04-16

### Changed
* Client now has two tabs for + and - deltas, which improves their shortcut key access.
* Minor tweaks and bug fixes.


## [0.6.0] - 2021-04-14

### Added
* Questions can be given custom labels in the spec file.  These will generally be used instead of "Q1", "Q2", etc.
* `plom-demo` now has `--port` option.
* New `plom-build rubric` subcommand can upload/download rubric lists from the server.

### Changed
* The left-hand-on-mouse option has been removed from annotator/marker - replaced with general key-binding options.
* Significant changes to rubrics: now shared between users and can be grouped into "tabs" within the user interface.
* Client: "Deltas" are now a special kind of rubric with their own tab.
* New client default keybindings involve a "spatial navigation" metaphor: left-right between tabs, up-down between rubrics.
* Rubrics are not longer saved on disc on client systems.
* Client: click-and-drag associates a rubric with a box on the page: no need for shift-modifier key as before.
* Client: The escape-key will now cancel an annotation mid-draw (box, ellipse, line, arrows, rubric)
* Client: There is no longer an explicit choice of "marking up/down mode" - it is determined by the rubrics used.
* Changed order of commands to start server: `plom-server init` now should be run before `plom-build parse`.


## [0.5.21] - 2021-03-18

### Changed
* Server has more flexibility in creating demo/auto users with `--auto` and new `--auto-named`.

### Fixed
* Misc fixes.


## [0.5.19] - 2021-03-09

### Changed
* Client rubrics list can no longer use drag-n-drop to reorder: this feature will return in 0.6.0, but for now its too buggy.

### Fixed
* Misc bug fixes and UI tweaks.
* LaTeX appears smoother on non-white backgrounds.
* Important dependency bumps including a aiohttp security fix.


## [0.5.18] - 2021-03-02

### Added
* Client shows path information in the Options dialog.
* Server: one can defer choosing number of papers until the classlist is uploaded by using "-1" for numberToName and/or numberToPrint.

### Changed
* Client background/uploader can operate in parallel.
* Client no longer looks for config file in the current folder.  The Options dialog shows config and log locations.


## [0.5.17] - 2021-02-10

### Added
* `plom-hwscan -q all` will upload a paper to all questions, a common operation for self-scanned work.

### Fixed
* Fix a crash with rearranger dialog revisiting a view with re-orientated pages.
* Rearranger dialog can load previously re-oriented pages.
* Misc fixes.


## [0.5.16] - 2021-01-29

### Changed
* Rotations in the adjust-pages dialog are now done in metadata.

### Fixed
* Client: fixed regression loading the default comment file.
* Improve testing of minimum versions of dependencies.


## [0.5.15] - 2021-01-25

### Added
* Annotation colour defaults to red but can be changed in the Annotator menu.

### Changed
* Untested scikit-learn used by default for digit recognition.  Tensorflow code still present and could return as default, after someone tests both on real data.
* Client: Ctrl-return forces LaTeX rendering of text annotations.
* Client: saves config file and comments in a central location.

### Fixed
* Flatpak client can save config and comment files.
* Fixed paper generation by working around a bug present in certain versions of `pymupdf` library.


## [0.5.13] - 2021-01-06

### Fixed
* Patched a memory leak when using the "adjust pages" dialog.
* Small fixes for various crashes.


## [0.5.11] - 2020-12-16

### Added
* `plom-hwscan` can now upload pages to multiple questions, for use with self-scanned work.

### Changed
* `plom-build make` now outputs a csv file showing the test numbers, question/page versions and student-info if named paper.
* `plom-build make --without-qr` builds pdf files without QR codes stamped on them.
* `plom-build make --no-pdf` builds everything but the PDF files are 0-length files.

### Fixed
* Adjust-Pages: fix deduping when shared page not included in current question.
* Fixed some times in manager tool.


## [0.5.10] - 2020-12-06

### Fixed
* Various fixes and minor refactoring.


## [0.5.9] - 2020-11-27

### Changed
* Adjust Pages dialog labels pages that are shared between questions.
* Minor UI tweaks.

### Fixed
* Fixed a platform-specific crash on start-up due to invalid chars in log filename.


## [0.5.8] - 2020-11-25

### Added
* Annotator: shift-drag with comment tool draws a highlighting box which is then connected to the rubric element.
* Annotator: page now has a margin to allow more space for annotations.  The additional space is cropped on submission.
* Finishing tools: support salted hashes for return codes on the command line.

### Changed
* Accept QR-coded pages that are landscape.
* Returned PDF files are often much smaller b/c reassembly now tries both png and jpeg.
* Server: more logging during authentication, including client version.
* Adjust Pages: dialog allows multiple selections for add/remove.
* Adjust Pages: you can have no pages transiently while re-arranging.
* Adjust Pages: icons resize automatically on dialog resize.
* Adjust Pages: middle bar can be dragged to resize top or bottom list.
* Client generates log files by default (disable under More Options).

### Fixed
* Misc fixes and refactoring of the `pagescene` code.
* API: refactoring for simpler image download code.
* Adjust Pages: re-entering dialog shows the current state instead of the original state.


## [0.5.7] - 2020-11-07

### Fixed
* Fix stale-pages from previous papers appearing in the Adjust Pages dialog.


## [0.5.6] - 2020-11-06

### Added
* Preliminary support for changing the overall scale of annotations; adjust using the menu/shortcut keys.

### Changed
* "Rearrange Pages" is now called "Adjust Pages" with a more prominent button.

### Fixed
* "Adjust Pages" dialog now opens faster, in some cases much faster.
* Other misc fixes and minor UI tweaks.


## [0.5.5] - 2020-10-23

### Changed
* Fix crash when drag-and-drop comments.


## [0.5.3] - 2020-10-22

### Added
* Scan now has command line arguments to enable/disable bitmap (jpeg) extraction.
* Server now logs failed token authentication events.

### Changed
* Opening the "Rearrange Pages" dialog displays a wait cursor as it may take some time.
* New command line arguments for `plom-finish` for digital return.
* Canvas-related return code handing reduced from 12 digits to 9 by default.
* Scan white balancing disabled by default (now matches `hwscan` behaviour).
* Scan bitmap extraction disabled by default (again to match `hwscan`).
* The database now creates Annotation entries upon client submission rather than task assignment.

### Fixed
* Fixed drag-and-drop reordering of the rubric/comment list.
* Fixed a bug where reannotating a reannotated paper from previous session doubled the underlying pages.
* Various bug fixes.


## [0.5.2] - 2020-10-06

### Added
* A collection of utility scripts now ships in `share/plom/contrib`.

### Changed
* Command-line utilities can load credentials from environment variables.

### Fixed
* There are now constraints on the returned image resolution preventing huge return images in some cases.
* Fixed crashes related to deleting comments.
* Various bug fixes.


## [0.5.1] - 2020-09-25

### Added
* Annotator: Ctrl-r shortcut key for Rearrange Pages tool.

### Changed
* `plom-hwscan` has command line arguments for gamma shift, off by default as it sometimes worsens already poor scans with large shadows.
* `plom-hwscan` does not extract jpeg's by default (it may in the future).
* `plom-hwscan` has new command line arguments for jpeg extraction.

### Fixed
* Workaround for bug in PyMuPDF 1.17.6.
* Various packaging improvements and fixes.
* "Rearrange Pages" dialog resizing improved.


## [0.5.0] - 2020-08-26

### Added
* Client now has a menu button for less-commonly used commands.
* Client can now insert small images, see "insert image" in menu.
* Client has experimental "Rearrange pages" dialog to fine-tune page selection and layout.
* We again offer prebuilt client binaries for some OSes.
* Server has new experimental "Homework mode" to deal with student-scanned images.
* Server can use Scikit-learn (instead of the default TensorFlow) for reading student numbers.

### Changed
* Command line utilities can report their version.
* Example demo data uses handwritten digits instead of fonts.
* Annotator remains open between papers.
* Totaller client was removed.
* ID-subclient - student name + id is entered in single field which auto-completes on both.
* Client sidebar can be set to the left or right (independent of mouse handedness).
* Grades output filename is now "marks.csv".
* Changes to various command-line tools to streamline uploading and other operations.
* Scanning is now based more strongly on concept of "bundles" of papers.
* Most tools now interact with the server via the API instead of using the file system.
* Server docker image uses pinned dependency information for reproducibility.
* Server, Manager and Client handling of "unknown" pages has improved.
* Client has visual feedback for ctrl-, shift- tool alternatives via mouse cursor.
* Various client UI tweaks.
* Various improvements to the manager UI tool.

### Fixed
* Fix left-hand mouse mode.
* Annotation font sizes no longer directly depend on UI font size (but some issues still remain).
* Pan mode no longer incorrectly moves objections.
* Many other bug fixes.


## [0.4.2] - 2020-04-21

### Added
* User-management can be performed by the manager client.

### Changed
* Greater fidelity to the original scan because JPEG files are (carefully) extracted and used directly.
* JPEG transformations are done without lossy re-encoding, when possible.
* PNG files should be a little smaller with fewer interpolation artifacts in the reass
* User credentials now handled by database rather than separate authentication object.
* Client can no longer revert; this feature may return later if needed.

### Fixed
* Various bug fixes.


## [0.4.1] - 2020-04-13

### Added
* Re-enabled the automatic IDing of papers using machine learning.
* Python package has improved dependency information.
* `plom-demo` checks if server is running and warns if directory isn't empty.
* Appdata metadata added for Plom Client.

### Changed
* Manager UI tool has better reporting of what users are doing.
* Manager and command line tools report papers that are marked "out"; this may be useful in case of client crashes, to identify (and reset) papers marking out for grading/IDing.
* Update for new plomgrading.org domain name.
* Remove testing tool dependencies on xvfb.

### Fixed
* Fixed toml dependency in Dockerfile.
* Various misc fixes.


## [0.4.0] - 2020-04-04

### Added
* Plom is now a python package.
* Annotator has a "no answer given" button which places crossed lines on page, leaves a comment, sets mark to 0.
* Client can log to a file (set under "More options").
* Client has expert option to disable background upload/download.
* Client can generate a log file for debugging.
* Server management UI.
* Command-line scripts for creating tests, managing server, scanning, and finishing.
* Simple toy test+server for demonstrating Plom.
* Test-specification now has "do-not-mark" pages for formula-sheets and instruction pages.

### Changed
* Server: improved database.
* Server: new upload procedure/tools.
* Reassembly tasks are now faster.
* Client: if there are annotations, confirm before closing/cancelling.

### Fixed
* Server: manager-related database locks fixed.
* In some regrade cases, delta-comments did not apply correctly.
* Client: fix `ctrl-=` zoom toggle.
* Various bug fixes.


## [0.3.0] - 2020-02-10

### Added
* saved comments are filtered per question and per test.
* Marker has a "view" button to look at any test number.

### Changed
* The manual-identifier now has a "discard" option for unneeded page images, such as blank extra pages.
* More robust networking by moving to https (rather than raw sockets). This is handled by the "requests" library on the client side and the "aiohttp" library on the server side.
* Client: config and saved comments now more human-readable in toml files.
* Client: can download test/server info before logging in.
* Client is more pessimistic about errors and will crash instead of trying to continue
in most cases.
* Client checks for double-logins and can force logout a previous session.
* Client: you must make at least one annotation on the page.

### Fixed
* Many fixes, especially related to client crashes due to networking.


## [0.2.2] - 2019-11-29

### Added
* Can now build papers with student Names/IDs pre-written on page 1.
* Client now has a "view" button to quickly view other questions.

### Changed
* Warning given for non-Latin names in classlist (may cause problems in PDFs).

### Fixed
* Annotator mark up/down and handedness preferences now saved between sessions.


## [0.2.1] - 2019-11-11

### Added
* preliminary support for a canned user list.
* autogenerate password suggestions for new users.
* 05 script now warns about potential extra pages.
* Annotator - spacebar pans through paper (down and right), shift-space pans back (up and left). Ctrl+space, Ctrl-shift-space does similarly but more slowly.
* Annotator - zoom-mode click-drag creates a (temp) rectangle to zoom into.

### Changed
* make 04 script less verbose.
* Increase timeout on server ping test.
* Annotator has more keybindings for grades of 0-10 (see "key help").
* resizing annotator persists between papers.
* zooming annotator persists between papers.
* docs: changes for uploading to the new Canvas gradebook.
* Annotator - can no longer click in region around score-box. This prevents accidentally pasting objects behind the scorebox.

### Fixed
* fixed race conditions when/uploading and downloading.
* certain file transfers are more robust at reporting errors.
* userManager was failing to start.
* return to greeter dialog on e.g., wrong server or pagegroup/version out of range.
* `mark_reverter` less fragile if files do not exist.
* if you skip identifying a test, the client will defer it until the end.
* identifying has various other UI fixes.


## [0.2.0] - 2019-10-11

### Added

#### Client
* delete tool: right-mouse button drag sweeps out a rectangle and deletes its contents.
* improve zoom ("ctrl-=" cycles through zoom modes).
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
* general GUI improvements.

#### Server
* Server not backward compatible with v0.1.0 clients.
* More general support for student names.
* Returned PDF files have better sizes for printing hardcopies.

### Fixed

* Many many bugfixes.


## 0.1.0 - 2019-06-26

This is the first release of Plom, Paperless Open Marking.


[0.15.5]: https://gitlab.com/plom/plom/-/compare/v0.15.5...v0.15.6
[0.15.5]: https://gitlab.com/plom/plom/-/compare/v0.15.4...v0.15.5
[0.15.4]: https://gitlab.com/plom/plom/-/compare/v0.15.3...v0.15.4
[0.15.3]: https://gitlab.com/plom/plom/-/compare/v0.15.2...v0.15.3
[0.15.2]: https://gitlab.com/plom/plom/-/compare/v0.15.1...v0.15.2
[0.15.1]: https://gitlab.com/plom/plom/-/compare/v0.15.0...v0.15.1
[0.15.0]: https://gitlab.com/plom/plom/-/compare/v0.14.8...v0.15.0
[0.14.8]: https://gitlab.com/plom/plom/-/compare/v0.14.7...v0.14.8
[0.14.7]: https://gitlab.com/plom/plom/-/compare/v0.14.6...v0.14.7
[0.14.6]: https://gitlab.com/plom/plom/-/compare/v0.14.5...v0.14.6
[0.14.5]: https://gitlab.com/plom/plom/-/compare/v0.14.4...v0.14.5
[0.14.4]: https://gitlab.com/plom/plom/-/compare/v0.14.3...v0.14.4
[0.14.3]: https://gitlab.com/plom/plom/-/compare/v0.14.2...v0.14.3
[0.14.2]: https://gitlab.com/plom/plom/-/compare/v0.14.1...v0.14.2
[0.14.1]: https://gitlab.com/plom/plom/-/compare/v0.13.3...v0.14.1
[0.13.3]: https://gitlab.com/plom/plom/-/compare/v0.13.2...v0.13.3
[0.13.2]: https://gitlab.com/plom/plom/-/compare/v0.13.1...v0.13.2
[0.13.1]: https://gitlab.com/plom/plom/-/compare/v0.13.0...v0.13.1
[0.13.0]: https://gitlab.com/plom/plom/-/compare/v0.12.3...v0.13.0
[0.12.3]: https://gitlab.com/plom/plom/-/compare/v0.12.2...v0.12.3
[0.12.2]: https://gitlab.com/plom/plom/-/compare/v0.12.1...v0.12.2
[0.12.1]: https://gitlab.com/plom/plom/-/compare/v0.12.0...v0.12.1
[0.12.0]: https://gitlab.com/plom/plom/-/compare/v0.11.1...v0.12.0
[0.11.1]: https://gitlab.com/plom/plom/-/compare/v0.11.0...v0.11.1
[0.11.0]: https://gitlab.com/plom/plom/-/compare/v0.10.1...v0.11.0
[0.10.1]: https://gitlab.com/plom/plom/-/compare/v0.10.0...v0.10.1
[0.10.0]: https://gitlab.com/plom/plom/-/compare/v0.9.4...v0.10.0
[0.9.4]: https://gitlab.com/plom/plom/-/compare/v0.9.3...v0.9.4
[0.9.3]: https://gitlab.com/plom/plom/-/compare/v0.9.2...v0.9.3
[0.9.2]: https://gitlab.com/plom/plom/-/compare/v0.9.0...v0.9.2
[0.9.0]: https://gitlab.com/plom/plom/-/compare/v0.8.11...v0.9.0
[0.8.11]: https://gitlab.com/plom/plom/-/compare/v0.8.10...v0.8.11
[0.8.10]: https://gitlab.com/plom/plom/-/compare/v0.8.8...v0.8.10
[0.8.8]: https://gitlab.com/plom/plom/-/compare/v0.8.7...v0.8.8
[0.8.7]: https://gitlab.com/plom/plom/-/compare/v0.8.6...v0.8.7
[0.8.6]: https://gitlab.com/plom/plom/-/compare/v0.8.5...v0.8.6
[0.8.5]: https://gitlab.com/plom/plom/-/compare/v0.8.2...v0.8.5
[0.8.2]: https://gitlab.com/plom/plom/-/compare/v0.8.1...v0.8.2
[0.8.1]: https://gitlab.com/plom/plom/-/compare/v0.8.0...v0.8.1
[0.8.0]: https://gitlab.com/plom/plom/-/compare/v0.7.12...v0.8.0
[0.7.12]: https://gitlab.com/plom/plom/-/compare/v0.7.11...v0.7.12
[0.7.11]: https://gitlab.com/plom/plom/-/compare/v0.7.9...v0.7.11
[0.7.9]: https://gitlab.com/plom/plom/-/compare/v0.7.7...v0.7.9
[0.7.7]: https://gitlab.com/plom/plom/-/compare/v0.7.5...v0.7.7
[0.7.5]: https://gitlab.com/plom/plom/-/compare/v0.7.4...v0.7.5
[0.7.4]: https://gitlab.com/plom/plom/-/compare/v0.7.3...v0.7.4
[0.7.3]: https://gitlab.com/plom/plom/-/compare/v0.7.2...v0.7.3
[0.7.2]: https://gitlab.com/plom/plom/-/compare/v0.7.1...v0.7.2
[0.7.1]: https://gitlab.com/plom/plom/-/compare/v0.7.0...v0.7.1
[0.7.0]: https://gitlab.com/plom/plom/-/compare/v0.6.5...v0.7.0
[0.6.5]: https://gitlab.com/plom/plom/-/compare/v0.6.4...v0.6.5
[0.6.4]: https://gitlab.com/plom/plom/-/compare/v0.6.3...v0.6.4
[0.6.3]: https://gitlab.com/plom/plom/-/compare/v0.6.2...v0.6.3
[0.6.2]: https://gitlab.com/plom/plom/-/compare/v0.6.1...v0.6.2
[0.6.1]: https://gitlab.com/plom/plom/-/compare/v0.6.0...v0.6.1
[0.6.0]: https://gitlab.com/plom/plom/-/compare/v0.5.21...v0.6.0
[0.5.21]: https://gitlab.com/plom/plom/-/compare/v0.5.19...v0.5.21
[0.5.19]: https://gitlab.com/plom/plom/-/compare/v0.5.18...v0.5.19
[0.5.18]: https://gitlab.com/plom/plom/-/compare/v0.5.17...v0.5.18
[0.5.17]: https://gitlab.com/plom/plom/-/compare/v0.5.16...v0.5.17
[0.5.16]: https://gitlab.com/plom/plom/-/compare/v0.5.15...v0.5.16
[0.5.15]: https://gitlab.com/plom/plom/-/compare/v0.5.13...v0.5.15
[0.5.13]: https://gitlab.com/plom/plom/-/compare/v0.5.11...v0.5.13
[0.5.11]: https://gitlab.com/plom/plom/-/compare/v0.5.10...v0.5.11
[0.5.10]: https://gitlab.com/plom/plom/-/compare/v0.5.9...v0.5.10
[0.5.9]: https://gitlab.com/plom/plom/-/compare/v0.5.8...v0.5.9
[0.5.8]: https://gitlab.com/plom/plom/-/compare/v0.5.7...v0.5.8
[0.5.7]: https://gitlab.com/plom/plom/-/compare/v0.5.6...v0.5.7
[0.5.6]: https://gitlab.com/plom/plom/-/compare/v0.5.5...v0.5.6
[0.5.5]: https://gitlab.com/plom/plom/-/compare/v0.5.3...v0.5.5
[0.5.3]: https://gitlab.com/plom/plom/-/compare/v0.5.2...v0.5.3
[0.5.2]: https://gitlab.com/plom/plom/-/compare/v0.5.1...v0.5.2
[0.5.1]: https://gitlab.com/plom/plom/-/compare/v0.5.0...v0.5.1
[0.5.0]: https://gitlab.com/plom/plom/-/compare/v0.4.2...v0.5.0
[0.4.2]: https://gitlab.com/plom/plom/-/compare/v0.4.1...v0.4.2
[0.4.1]: https://gitlab.com/plom/plom/-/compare/v0.4.0...v0.4.1
[0.4.0]: https://gitlab.com/plom/plom/-/compare/v0.3.0...v0.4.0
[0.3.0]: https://gitlab.com/plom/plom/-/compare/v0.2.2...v0.3.0
[0.2.2]: https://gitlab.com/plom/plom/-/compare/v0.2.1...v0.2.2
[0.2.1]: https://gitlab.com/plom/plom/-/compare/v0.2.0...v0.2.1
[0.2.0]: https://gitlab.com/plom/plom/-/compare/v0.1.0...v0.2.0
