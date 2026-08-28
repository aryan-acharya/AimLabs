#version 330 core

in vec2 in_position;
out vec2 texcoord;

void main() {
    texcoord = in_position * 0.5 + 0.5;
    gl_Position = vec4(in_position, 0.999, 1.0);
}
