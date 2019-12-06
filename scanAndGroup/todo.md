# Notes on what to do - CBM & ADR Dec 6.

## Workflow.

* User produces a bundle scan `blah.pdf`.
* After (successful) processing the bundle is moved to an `archivePDFs` directory.
* Before processing the scan - check old bundles in archive - by both filename and md5sum.
  * if md5sum same then tell user and do not process.
  * if filename same then tell user to rename before processing.
* store md5sum of bundle as well as m5sum of pageimage. Name as `blah-n.png`.

* Initial QR code read of each pageimage
  * If no QR code - then file (somehow) as `unknown`
  * If QRcode with matching magic code - file as `tXXXXpYYvZ.blah-n.png` (to keep of which bundle-file it came from)
  * If QRcode with wrong magic code - then file in `wrongTest` directory.

* At this stage we should have 3 sets of files
  1. Valid TPV files
  2. Unknown - probably these are extra pages, but could also just be QR-code errors.
  3. Wrong test file - these can be discarded (after user warning).

* PushValid - send TPV, the PNG, md5sum of both image + bundle to server.
  * All ok - server sends back an "all ok"
  * Duplicate TPV - server checks md5sums to make sure this is actually a different file.
    * if same file - then ignore it.
    * if new file but duplicate TPV then report to user - server files in DUPLICATES.

* PushUnknown - send PNG, md5sum of image+bundle.
    * Server sends back an ok.

## Page image lifecycle
1. User brings in a new bundlePDF. Once processed it moves to `archive` directory
2. the bundle is split into png-pages which live in `pageImages`
3. Each png has its QRs read and md5sum computed.
4. PNG+QR+md5sum sent to server for filing.
5. If successful - PNG moved into `sentImages` directory
6. At some point the files in `sentImages` are cleaned-up - ie deleted.
7. Note that this means we keep the PDF-bundles, but no pageimages once uploaded to server.

## Database hackery
0. Each object set needs a unique integer identifier (as well as what ever else we make up)
1. Markdata - needs to support regrades. ie - each regrade of a paper should be a separate Markdata instance.
2. UnknownPages - pageImages that are yet to be identified as either extras or TPVs
3. Duplicates - pages that are duplicates of TPVs already uploaded. 
