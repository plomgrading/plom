htmlsrc = """
<!DOCTYPE html>
<!-- Copyright (C) 2018-2021 Colin B. Macdonald <cbm@m.fsf.org>-->
<!-- SPDX-License-Identifier: FSFAP -->
<!--
     Copying and distribution of this file, with or without modification,
     are permitted in any medium without royalty provided the copyright
     notice and this notice are preserved.  This file is offered as-is,
     without any warranty.
-->
<html lang="en" dir="ltr" class="client-nojs">
<head>
<title>__COURSENAME__ - Online Return</title>

<meta charset="UTF-8" />
<style>
body {
    padding: 2em;
}

label {
    font-weight: bold;
    font-style: italic;
        font-size: medium;
    width: 12em;
    display: inline-block;
}

button {
    font-weight: bold;
    margin-top: 1em;
    line-height: 2;
}

</style>

<script>
    function retrievePaper() {
        var id = document.getElementById('studentID').value;
        if( !id || id.length!=__SID_LENGTH__ ) {
            alert("Invalid student number!");
            return;
        }
        var code = document.getElementById('studentCode').value;
        code = code.replace(/,/g,'')
        if( !code || code.length!=__CODE_LENGTH__ ) {
            alert("Invalid code!");
            return;
        }
        var which = '__TESTNAME__'
        window.location.href = which+"_"+id+"_"+code+".pdf";
    }
</script>
</head>



<body>
<hr>
<h1>__COURSENAME__ - Online Return</h1>

<p>This form can be used to retrieve an electronic copy of your paper.</p>

<hr>

<p>In order to access your paper you need to fill in your student number and
your __CODE_LENGTH__-digit &ldquo;return code&rdquo; from <a href="http://canvas.ubc.ca">canvas</a>.</p>


<p><i>NOTE:</i> the request will fail if incorrect information is entered.<p>

<div>
    <label class="label" for="studentID">Student number: </label>
    <input id="studentID" name="studentID" type="text" maxlength="__SID_LENGTH__" />
</div>
<br>
<div>
    <label class="label" for="studentCode">Code: </label>
    <input id="studentCode" name="studentCode" type="text" />
</div>
<br>
<div>
    <label class="label" for="retrieve"></label>
    <button id="retrieve" name="retrieve" onclick="retrievePaper()" type="button">Retrieve paper</button>
</div>
<div>

<hr>
</body>
</html>
"""


htmlsrc_w_solutions = """
<!DOCTYPE html>
<!-- Copyright (C) 2018-2021 Colin B. Macdonald <cbm@m.fsf.org>-->
<!-- SPDX-License-Identifier: FSFAP -->
<!--
     Copying and distribution of this file, with or without modification,
     are permitted in any medium without royalty provided the copyright
     notice and this notice are preserved.  This file is offered as-is,
     without any warranty.
-->
<html lang="en" dir="ltr" class="client-nojs">
<head>
<title>__COURSENAME__ - Online Return</title>

<meta charset="UTF-8" />
<style>
body {
    padding: 2em;
}

label {
    font-weight: bold;
    font-style: italic;
    font-size: medium;
    width: 12em;
    display: inline-block;
}

button {
    font-weight: bold;
    margin-top: 1em;
    line-height: 2;
}

</style>

<script>
    function retrievePaper() {
        var id = document.getElementById('studentID').value;
        if( !id || id.length!=__SID_LENGTH__ ) {
            alert("Invalid student number!");
            return;
        }
        var code = document.getElementById('studentCode').value;
        code = code.replace(/,/g,'')
        if( !code || code.length!=__CODE_LENGTH__ ) {
            alert("Invalid code!");
            return;
        }
        var which = '__TESTNAME__'
        window.location.href = which+"_"+id+"_"+code+".pdf";
    }
    function retrieveSolution() {
        var id = document.getElementById('studentID').value;
        if( !id || id.length!=__SID_LENGTH__ ) {
            alert("Invalid student number!");
            return;
        }
        var which = '__TESTNAME__'
        window.location.href = which+"_solutions_"+id+".pdf";
}
</script>
</head>



<body>
<hr>
<h1>__COURSENAME__ - Online Return</h1>

<p>This form can be used to retrieve an electronic copy of your paper.</p>

<hr>

<p>In order to access your paper you need to fill in your student number and
your __CODE_LENGTH__-digit &ldquo;return code&rdquo; from <a href="http://canvas.ubc.ca">canvas</a>.</p>


<p><i>NOTE:</i> the request will fail if incorrect information is entered.<p>

<div>
    <label class="label" for="studentID">Student number: </label>
    <input id="studentID" name="studentID" type="text" maxlength="__SID_LENGTH__" />
</div>
<br>
<div>
    <label class="label" for="studentCode">Code: </label>
    <input id="studentCode" name="studentCode" type="text" />
</div>
<br>
<div>
    <label class="label" for="retrieve"></label>
    <button id="retrieve" name="retrieve" onclick="retrievePaper()" type="button">Retrieve paper</button>
</div>
<br>
<div>
    <label class="label" for="solution"></label>
    <button id="solution" name="solution" onclick="retrieveSolution()" type="button">Retrieve solutions</button>
</div>
<div>

<hr>
</body>
</html>
"""
