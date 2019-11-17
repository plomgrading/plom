# URLs used for the PLOM API

## TODOs
* build a proper API document which shows inputs and return values etc.

## Authentication + Version
* get "/Version" - return server+API versions as test string
* put "/users/{user}" - verify user/password + return auth-token
* delete "/users/{user}" - close user-session + revoke auth-token

## Identifier
* get "/ID/progress" - return [#done, #total]
* get "/ID/tasks/available" - return [next available task] or 204-code (if none)
* get "/ID/classlist" - return classlist file
* get "/ID/predictions" - return prediction-list file
* get "/ID/tasks/complete" - return list of tasks completed by that user
* get "/ID/images/{tgv}" - return the image-file for that TGV
* patch "/ID/tasks/{task}" - claim task (if still available) - return imagefile
* put "/ID/tasks/{task}" - update the ID/Name of the task (ie test)
* delete "/ID/tasks/{task}" - unclaim task - ie tell server that user did not finish that task - go back on todo list

## Totaller
* get "/TOT/maxMark" - return max-total-mark for test
* get "/TOT/progress" - return [#done, #total]
* get "/TOT/tasks/complete" - return list of tasks completed by that user
* get "/TOT/tasks/available" - return [next available task] or 204-code (if none)
* get "/TOT/images/{tgv}" - return imagefile of that tgv
* patch "/TOT/tasks/{task}" - claim task (if still available) - return imagefile
* put "/TOT/tasks/{task}" - update the mark of the task (ie test)
* delete "/TOT/tasks/{task}" - unclaim task

## Marker
* get "/MK/maxMark" - return max-mark for the page-group
* get "/MK/progress" - return [#done, #total]
* get "/MK/tasks/complete" - return list of tasks completed by that user
* get "/MK/tasks/available" - return next available task
* get "/MK/latex" - take latex-fragment, process and return png
* get "/MK/images/{tgv}" - return imagefile of that tgv
* get "/MK/whole/{number}" - return group-images of entire paper (except id-page)
* patch "/MK/tags/{tgv}" - save user-tags of that tgv
* put "/MK/tasks/{tgv}" - send back marked-image, plom-file, comments, mark etc.
* patch "/MK/tasks/{task}" - claim the task (if still available) - return imagefile
* delete "/MK/tasks/{task}" - unclaim the task.
