#version 330 core

in vec2 frag_uv;

uniform sampler2D tex;
uniform vec4 color;
uniform bool use_texture;

out vec4 frag_color;

void main() {
    if (use_texture) {
        vec4 t = texture(tex, frag_uv);
        frag_color = t * color;
    } else {
        frag_color = color;
    }
}
