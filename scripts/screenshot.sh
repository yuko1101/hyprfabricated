#!/usr/bin/env sh

if [ -z "$XDG_PICTURES_DIR" ]; then
	XDG_PICTURES_DIR="$HOME/Pictures"
fi

scrDir=$(dirname "$(realpath "$0")")
save_dir="${2:-$XDG_PICTURES_DIR/Screenshots}"
save_file=$(date +'%y%m%d_%Hh%Mm%Ss_screenshot.png')
full_path="$save_dir/$save_file"
mkdir -p $save_dir

function print_error
{
	cat <<"EOF"
    ./screenshot.sh <action>
    ...valid actions are...
        p  : print all screens
        s  : snip current screen
        sf : snip current screen (frozen)
        m  : print focused monitor
EOF
}

case $1 in
p) # print all outputs
	grimblast copysave screen $full_path ;;
s) # drag to manually snip an area / click on a window to print it
	grimblast copysave area $full_path ;;
sf) # frozen screen, drag to manually snip an area / click on a window to print it
	grimblast --freeze copysave area $full_path ;;
m) # print focused monitor
	grimblast copysave output $full_path;;
*) # invalid option
	print_error ;;
esac


if [ -f "${save_dir}/${save_file}" ]; then
    notify-send -a "Fabric" -i "${full_path}" "Screenshot saved" "in ${full_path}/"
else
    notify-send -a "Fabric" "Screenshot Aborted"
fi
