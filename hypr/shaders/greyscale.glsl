#version 300 es
precision highp float;

in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 pixColor = texture(tex, v_texcoord);
    
    vec3 lumaCoeffs = vec3(0.212656, 0.715158, 0.072186);
    
    float luma = dot(lumaCoeffs, pixColor.rgb);
        fragColor = vec4(vec3(luma), pixColor.a);
}
