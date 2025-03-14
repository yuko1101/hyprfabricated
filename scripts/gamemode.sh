#!/usr/bin/env sh

HYPRGAMEMODE=$(hyprctl getoption animations:enabled | awk 'NR==1{print $2}')

if [ "$1" = "check" ]; then
    if [ "$HYPRGAMEMODE" = 0 ]; then
        echo 0
    else
        echo 1
    fi
    exit
fi

if [ "$1" = "toggle" ]; then
    if [ "$HYPRGAMEMODE" = 1 ]; then
        hyprctl --batch "\
            keyword animations:enabled 0;\
            keyword decoration:shadow:enabled 0;\
            keyword decoration:blur:enabled 0;\
            keyword general:gaps_in 0;\
            keyword general:gaps_out 0;\
            keyword general:border_size 1;\
            keyword decoration:rounding 0"
        exit
    fi
    hyprctl reload
    exit
fi

echo "Invalid argument. Use 'check' or 'toggle'."
