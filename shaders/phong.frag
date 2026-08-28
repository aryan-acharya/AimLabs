#version 330 core

in vec3 frag_pos;
in vec3 frag_normal;

uniform vec3  light_pos;
uniform vec3  cam_pos;
uniform vec3  object_color;
uniform float ambient_strength;
uniform float specular_strength;
uniform float hit_flash;        // 0.0-1.0 white flash on hit
uniform int   stripe_mode;      // 1 = yellow/black zebra stripes, 0 = solid color

out vec4 frag_color;

void main() {
    vec3 norm        = normalize(frag_normal);
    vec3 light_dir   = normalize(light_pos - frag_pos);
    vec3 view_dir    = normalize(cam_pos - frag_pos);
    vec3 reflect_dir = reflect(-light_dir, norm);

    // Base colour: solid or zebra stripes
    vec3 base_color;
    if (stripe_mode == 1) {
        // Horizontal bands driven by world Y — ~3 stripes across the sphere
        float band = mod(frag_pos.y * 2.5, 1.0);
        base_color = (band < 0.5)
            ? vec3(1.0, 0.85, 0.0)      // yellow
            : vec3(0.06, 0.06, 0.06);   // near-black
    } else {
        base_color = object_color;
    }

    // Phong shading
    vec3 ambient  = ambient_strength * base_color;

    float diff    = max(dot(norm, light_dir), 0.0);
    vec3  diffuse = diff * base_color * vec3(1.0, 0.95, 0.9);

    float spec    = pow(max(dot(view_dir, reflect_dir), 0.0), 32.0);
    vec3  specular = specular_strength * spec * vec3(1.0);

    vec3 result = ambient + diffuse + specular;

    // Hit flash: lerp toward white
    result = mix(result, vec3(1.0), hit_flash);

    frag_color = vec4(result, 1.0);
}
