REM SPDX-License-Identifier: AGPL-3.0-or-later
REM Copyright (C) 2024 Aidan Murphy

@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
if "%SPHINXOPTS%" == "" (
	set SPHINXOPTS=-j auto -v -W
)

set MODULES=plom_server plom
set SPHINXAPI=sphinx-apidoc
set SPHINXAPIOPTS=-d 1 -e -f

set SOURCEDIR=source
set BUILDDIR=build

if "%1" == "" goto help
if "%1" == "autodocs" goto autodocs

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.http://sphinx-doc.org/
	exit /b 1
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:autodocs
(for %%m in (%MODULES%) do (
   %SPHINXAPI% -o "%SPHINXAPI%/%%m" "../%%m" %SPHINXAPIOPTS% %O%
))
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd
