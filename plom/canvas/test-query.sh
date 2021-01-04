#!/usr/bin/zsh

# Where I'm storing my API key / the course ID
source api_secrets.sh

# Get list of courses associated to my account and write it to
# courselist.json
curl https://canvas.ubc.ca/api/v1/courses \
  -H "Authorization: Bearer ${FK_KEY}" \
  > courselist.json

# Similarly, but get a list of students for Colin's sandbox. Note,
# `SANDBOX_ID` was obtained by poking through `courselist.json`, but
# it also turns out to just be the course code in the URL bar on
# canvas.
#
# Note, all of this stuff below can probably be done automatically
# with some GraphQL wrangling etc., I just haven't read about how to
# do that yet
curl "https://canvas.ubc.ca/api/v1/courses/${SANDBOX_ID}/students"  \
  -H "Authorization: Bearer ${FK_KEY}" \
  > sandbox_student_list.json

# Similarly, but get a list of assignments for Colin's sandbox.
curl "https://canvas.ubc.ca/api/v1/courses/${SANDBOX_ID}/assignments"  \
  -H "Authorization: Bearer ${FK_KEY}" \
  > sandbox_assignment_list.json

# Using the return value from the assignment query above, figure out
# the name of the test assignment and get all submissions for it.
# Note, this doesn't download
curl "https://canvas.ubc.ca/api/v1/courses/${SANDBOX_ID}/assignments/${TEST_ASSIGNMENT_ID}/submissions"  \
  -H "Authorization: Bearer ${FK_KEY}" \
  > submissions.json

# Using the URL `TEST_ASSIGNMENT_SUBMISSION` obtained from
# `submissions.json`, follow a redirect to download the file with curl
# and write the output to `test-submission.pdf`
curl -L "${TEST_ASSIGNMENT_SUBMISSION}" > test-submission.pdf
