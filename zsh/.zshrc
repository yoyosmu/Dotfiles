export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git sudo archlinux extract)

if [[ -f $ZSH/oh-my-zsh.sh ]]; then
  source $ZSH/oh-my-zsh.sh
fi

source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh

alias grep='grep --color=auto'
alias ls='lsd'
alias fastfetch='anifetch -W 60 -H 35 ~/.local/share/anifetch/assets/example.mp4 -ff -c '--symbols wide --fg-only'' 
alias u='sudo pacman -Syu'
alias U='yay -Syu'
alias c='sudo pacman -Rns $(pacman -Qdtq) && yay -Ycc'
alias C='sudo rm -rf ~/.cache/* /var/cache/pacman/pkg/* /home/yoyomu/.cache/yay/*'
alias g='cd ~/dotfiles && git add . && git commit -m "Cool Stuff" && git pull origin main --rebase && git push origin main'
alias i='sudo pacman -S'
alias I='yay -S'

export PATH="$PATH:/home/yoyomu/.local/bin"


anifetch -W 60 -H 35 ~/.local/share/anifetch/assets/example.mp4 -ff -c '--symbols wide --fg-only'

eval "$(starship init zsh)"
