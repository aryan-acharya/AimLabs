#version 330 core

in vec2 in_position;
in vec2 in_uv;
out vec2 frag_uv;

uniform vec2 screen_size;
uniform vec2 offset;
uniform vec2 scale;

void main() {
    frag_uv = in_uv;
    vec2 pos = (in_position * scale + offset) / (screen_size * 0.5);
    gl_Position = vec4(pos, 0.0, 1.0);
}
