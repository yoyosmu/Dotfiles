#!/bin/bash

cava -p ~/.config/cava/waybar | while IFS=';' read -ra vals; do
    chars=""
    for val in "${vals[@]}"; do
        case $val in
            0) chars="${chars}▁" ;;
            1) chars="${chars}▂" ;;
            2) chars="${chars}▃" ;;
            3) chars="${chars}▄" ;;
            4) chars="${chars}▅" ;;
            5) chars="${chars}▆" ;;
            6) chars="${chars}▇" ;;
            7) chars="${chars}█" ;;
            8) chars="${chars}█" ;;

        esac
    done
    echo "$chars"
done
