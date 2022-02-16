#!/bin/bash

# Construct a standalone macOS MantidWorkbench .dmg bundle.
# The bundle is created from a pre-packaged conda version
# and removes any excess that is not necessary in a standalone
# bundle
set -e

# Constants
HERE="$(dirname "$0")"
BUILDDIR=_bundle_build
# Prefer mamba over conda for speed
CONDA_EXE=mamba
CONDA_PACKAGE=mantidworkbench

# Use otool/install_name_tool to change a dependent path
# to a reexported library. The original is assumed to contain
# an absolute path
#   $1 - Full Path to the .so/.dylib to fix
function fixup_reexport_dependent_path() {
  local libpath=$1
  local -r dependent_path=$(otool -l "${libpath}" | grep LC_REEXPORT_DYLIB -A 2 | grep name | awk '{print $2}')
  local -r dependent_fname=$(basename "${dependent_path}")

  echo "Fixing up LC_REEXPORT_DYLIB path in '$libpath'"
  install_name_tool -change "${dependent_path}" @rpath/"${dependent_fname}" "${libpath}"
}

# Add a key string-value pair to a plist
#  $1 - Full path to the plist
#  $2 - Key name
#  $3 - Key string value
function add_string_to_plist() {
  local filepath=$1
  local key=$2
  local string_value=$3
  /usr/libexec/PlistBuddy -c "Add :$key string $value" "$filepath"
}

# Print usage and exit
function usage() {
  local exitcode=$1
  echo "Usage: $0 [options] bundle_name icon_file"
  echo
  echo "Create a DragNDrop bundle out of a Conda package. The package is built in $BUILDDIR."
  echo "This directory will be created if it does not exist or purged if it already exists."
  echo "The final .dmg will be created in the current working directory."
  echo "Options:"
  echo "  -c Optional Conda channel overriding the default mantid"
  echo
  echo "Positional Arguments"
  echo "  bundle_name: The name of the bundle app directory, i.e. the final name will be '${bundle_name}.app'"
  echo "  icon_file: An icon file, in icns format, for the final bundle"
  exit $exitcode
}

# Optional arguments
conda_channel=mantid
while getopts ":c:h" o; do
  case "$o" in
  c) conda_channel="$OPTARG";;
  h) usage 0;;
  *) usage 1;;
esac
done
shift $((OPTIND-1))

# Positional arguments
# 2) - the name of the bundle
# 3) - path to .icns image used as icon for bundle
bundle_name=$1
bundle_icon=$2

# Sanity check arguments. Especially ensure that paths are not empty as we are removing
# items and we don't want to accidentally clean out system paths
test -n "$bundle_name" || usage 1
test -n "$bundle_icon" || usage 1

bundle_dirname="$bundle_name".app
bundle_contents="$BUILDDIR"/"$bundle_dirname"/Contents
echo "Building '$bundle_dirname' in '$BUILDDIR' from '$conda_channel' Conda channel"

# Build directory needs to be empty before we start
if [ -d "$BUILDDIR" ]; then
  echo "$BUILDDIR exists. Removing before commencing build."
  rm -fr "$BUILDDIR"
elif [ -e "$BUILDDIR" ]; then
  echo "$BUILDDIR exists but is not a directory. $BUILDDIR is expected to be created by this script as a place to build the bundle"
  echo "Either move/rename $BUILDDIR or use a different working directory"
  exit 1
fi

# Create basic directory structure.
mkdir -p "$bundle_contents"/{Resources,MacOS}

# Create conda environment internally. --copy ensures no symlinks are used
bundle_conda_prefix="$bundle_contents"/Resources

echo "Creating Conda environment in '$bundle_conda_prefix' from '$CONDA_PACKAGE'"
"$CONDA_EXE" create --prefix "$bundle_conda_prefix" --copy --channel "$conda_channel" --yes \
  "$CONDA_PACKAGE" \
  jq  # used for processing the version string

# Determine version information
version=$("$CONDA_EXE" list --prefix "$bundle_conda_prefix" '^mantid$' --json | jq --raw-output '.[0].version')

# Remove jq
"$CONDA_EXE" remove --prefix "$bundle_conda_prefix" --yes jq

# Certain packages use LC_REEXPORT_DYLIB rather than LC_LOAD_DYLIB for their dependents
# See http://blog.darlinghq.org/2018/07/mach-o-linking-and-loading-tricks.html for details.
# Conda install rewrites these LC_REEXPORT_DYLIB links with absolute links and breaks relocation
# This can easily be remedied by switching to use the @rpath identifier
# We avoid scanning the whole bundle as this potentially very expensive and instead fixup the libraries
# we know have issues
fixup_reexport_dependent_path "$(find "$bundle_conda_prefix" -name 'libncurses.*' -type f)"

# Conda bundles pretty much everything with each of its packages and much of this is
# unnecessary in this type of bundle - trim the fat.
echo "Purging '$bundle_conda_prefix' of unnecessary items"
# Heavily cut down everything in bin
mv "$bundle_conda_prefix"/bin "$bundle_conda_prefix"/bin_tmp
mkdir "$bundle_conda_prefix"/bin
cp "$bundle_conda_prefix"/bin_tmp/Mantid.properties "$bundle_conda_prefix"/bin/
cp "$bundle_conda_prefix"/bin_tmp/mantid-scripts.pth "$bundle_conda_prefix"/bin/
cp "$bundle_conda_prefix"/bin_tmp/MantidWorkbench "$bundle_conda_prefix"/bin/
cp "$bundle_conda_prefix"/bin_tmp/python "$bundle_conda_prefix"/bin/
cp "$bundle_conda_prefix"/bin_tmp/pip "$bundle_conda_prefix"/bin/
sed -i "" '1s|.*|#!/usr/bin/env python|' "$bundle_conda_prefix"/bin/pip
# Heavily cut down share
mv "$bundle_conda_prefix"/share "$bundle_conda_prefix"/share_tmp
# Removals
rm -rf "$bundle_conda_prefix"/bin_tmp \
  "$bundle_conda_prefix"/include \
  "$bundle_conda_prefix"/man \
  "$bundle_conda_prefix"/mkspecs \
  "$bundle_conda_prefix"/phrasebooks \
  "$bundle_conda_prefix"/qml \
  "$bundle_conda_prefix"/qsci \
  "$bundle_conda_prefix"/share_tmp \
  "$bundle_conda_prefix"/translations
find "$bundle_conda_prefix" -name 'qt.conf' -delete
find "$bundle_conda_prefix" -name '*.a' -delete
find "$bundle_conda_prefix" -name "*.pyc" -type f -delete
find "$bundle_conda_prefix" -path "*/__pycache__/*" -delete
find "$bundle_contents" -name '*.plist' -delete

# Add required resources
cp "$HERE"/BundleExecutable "$bundle_contents"/MacOS/"$bundle_name"
chmod +x "$bundle_contents"/MacOS/"$bundle_name"
cp "$HERE"/qt.conf "$bundle_conda_prefix"/bin/qt.conf
cp "$bundle_icon" "$bundle_conda_prefix"

# Create a plist from base version
bundle_plist="$bundle_contents"/Info.plist
cp "$HERE"/Info.plist.base "$bundle_plist"
add_string_to_plist "$bundle_plist" CFBundleIdentifier org.mantidproject."$bundle_name"
add_string_to_plist "$bundle_plist" CFBundleExecutable "$bundle_name"
add_string_to_plist "$bundle_plist" CFBundleName "$bundle_name"
add_string_to_plist "$bundle_plist" CFBundleIconFile "$(bundle_icon)"
add_string_to_plist "$bundle_plist" CFBundleVersion "$version"
add_string_to_plist "$bundle_plist" CFBundleLongVersionString "$version"

# Wrap up into dmg
version_name="$bundle_name"-"$version"
echo "Creating DragNDrop bundle '$version_name.dmg'"
hdiutil create -volname "$version_name" -srcfolder "$BUILDDIR" -ov -format UDZO "$version_name".dmg

echo
echo "Bundle '$bundle_name.dmg' successfully created."
