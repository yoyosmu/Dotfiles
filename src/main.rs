use rand::random;
use gtk4::prelude::*;
use gtk4::{Application, ApplicationWindow, Button, Label, Box, Orientation};

fn main() {
    let app = Application::builder()
        .application_id("org.yoyomu.hyprclicker")
        .build();

    app.connect_activate(build_ui);
    app.run();
}

fn build_ui(app: &Application) {
    let label= Label::builder() 
    	.label("Press the button")
    	.margin_bottom(10)
    	.margin_top(10)
    	.margin_start(10)
    	.margin_end(10)
        .build();
    
    let button = Button::builder()
    	.label("Flip coin")
    	.margin_bottom(50)
    	.margin_top(50)
    	.margin_start(50)
    	.margin_end(50)
        .build();

    let content = Box::new(Orientation::Vertical, 0);
        content.append(&label);
        content.append(&button);
        
    let window = ApplicationWindow::builder()
        .title("HyprClicker")
        .application(app)
        .child(&content)
        .build();

        content.set_size_request(200, 100);
        button.connect_clicked(move |_| flip_coin(&label));

        window.show();
}

fn flip_coin(label: &Label) {
    if random() {
        label.set_text("heads");
    } else {
        label.set_text("tails");	
    }
}

