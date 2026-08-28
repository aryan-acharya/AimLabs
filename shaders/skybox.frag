#version 330 core

in vec2 texcoord;

uniform float time;

out vec4 frag_color;

void main() {
    float t = texcoord.y;      // 0 = bottom, 1 = top

    // Deep space gradient: bottom = dark purple, top = very dark navy
    vec3 bottom_color = vec3(0.12, 0.05, 0.28);  // visible purple
    vec3 mid_color    = vec3(0.08, 0.06, 0.22);  // muted violet
    vec3 top_color    = vec3(0.02, 0.02, 0.12);  // dark navy

    vec3 sky;
    if (t > 0.5) {
        sky = mix(mid_color, top_color, (t - 0.5) * 2.0);
    } else {
        sky = mix(bottom_color, mid_color, t * 2.0);
    }

    // Subtle star shimmer (procedural)
    float seed = fract(sin(dot(texcoord * 500.0, vec2(12.9898, 78.233))) * 43758.5453);
    float star = step(0.995, seed);
    float shimmer = 0.5 + 0.5 * sin(time * 2.0 + seed * 100.0);
    sky += vec3(star * shimmer * 0.8);

    frag_color = vec4(sky, 1.0);
}
