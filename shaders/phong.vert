#version 330 core

in vec3 in_position;
in vec3 in_normal;

uniform mat4 m_model;
uniform mat4 m_view;
uniform mat4 m_proj;

out vec3 frag_pos;
out vec3 frag_normal;

void main() {
    vec4 world_pos = m_model * vec4(in_position, 1.0);
    frag_pos = world_pos.xyz;
    frag_normal = mat3(transpose(inverse(m_model))) * in_normal;
    gl_Position = m_proj * m_view * world_pos;
}
