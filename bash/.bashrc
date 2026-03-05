#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '

[[ $- == *i* ]] && source /usr/share/blesh/ble.sh

export FZF_DEFAULT_OPTS=" \
--color=bg+:#252525,bg:#242423,spinner:#97bb98,hl:#97bb98 \
--color=fg:#DDDAD3,header:#9fbdde,info:#989772,pointer:#feffff \
--color=marker:#97bb98,fg+:#feffff,prompt:#97bb98,hl+:#feffff \
--multi --border --layout=reverse --height=40% --inline-info"

eval "$(starship init bash)"

complete -d -X '.[^./]*' cd
complete -f lsd
complete -F _minimal micro

# Created by `pipx` on 2025-10-30 22:41:38
export PATH="$PATH:/home/yoyomu/.local/bin"

alias fastfetch='anifetch example.mp4 -ff'
alias u='sudo pacman -Syu'
alias U='yay -Syu'
alias c='sudo pacman -Rns $(pacman -Qdtq) && yay -Ycc'
alias C='sudo rm -rf ~/.cache/* /var/cache/pacman/pkg/* /home/yoyomu/.cache/yay/*'
alias g='cd ~/dotfiles && git add . && git commit -m "Cool Stuff" && git pull origin main --rebase && git push origin main'
alias i='sudo pacman -S'
alias I='yay -S'
alias ls='lsd'
