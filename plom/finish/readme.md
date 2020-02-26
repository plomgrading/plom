## Files n things
* reassembled = directory that will contain the reassembled and marked papers.

* coverPages = directory that contains the front pages (containing student info + marks) for each completed paper.

* 07_check_completed - this script checks to see which of the exams scanned and grouped have been id'd and marked in their entirety. If a paper has been completed, then a coverpage is produced, and globbed together with the id pages and the pagegroup to form a reassembled exam. That exam is stored in the 'reassembled' directory and saved as 'exam_X.pdf' where X is the student number.
 * The cover page consists of
   * student number
   * student name
   * table of marks for each page group
   * the version of each pagegroup is given
   * the total mark for the paper.
 * This script should likely be split up into (checking that things are completed), (reassembling completed papers), and then (renaming completed papers).
   * this last step might file papers as 'exam_X.pdf' where X=student number, but one might also use 'exam_X_C.pdf'  where X=student number and C=exam code.
   * having an exam code makes returning the exam via a simple javascript page much easier. It avoids us having to build an authenticated page. Upload the codes to whatever LMS you are using, then students can simply enter their number+code into a webpage and be served their exam pdf.
