# AimLabs 3D

AimLabs 3D is a Python first-person aim trainer built on ModernGL and Pygame.

This README is a full technical map of the current codebase: how rendering works, what each shader does, what each Python file owns, and how modules depend on each other.

## Quick Start

```bash
cd aimlabs

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

Requirements:
- Python 3.10+
- OpenGL 3.3 capable GPU/driver

## Runtime Controls

| Input | Action |
|---|---|
| Left Click | Shoot, start round, resume from pause |
| Mouse Move | Look/aim |
| W A S D | Move |
| Left Shift | Sprint |
| R | Manual reload (when mag not full) |
| ESC | Pause during gameplay |
| ESC while paused | Quit game |
| R on end screen | Restart |

Notes:
- Timer starts on first shot, not on app start.
- Gameplay uses sphere targets in one arena mode.

## Libraries Used

| Library | Where | Why |
|---|---|---|
| moderngl | engine + main | OpenGL context operations, shader programs, VBO/IBO/VAO, textures, draw calls |
| pygame | engine + main + renderer + sound | Window/input/audio/font surfaces and per-frame events |
| numpy | engine + game | Vector and matrix buffers, numeric simulation, procedural sound synthesis |
| pyrr | main + camera + gun | Matrix creation for view/projection/model transforms |

## File and Module Dependency Map

### Top-level orchestration
- main.py
    - imports engine.window.Window
    - imports engine.camera.Camera
    - imports engine.shader.ShaderManager
    - imports engine.mesh meshes
    - imports engine.renderer.HUDRenderer
    - imports all game systems (target, obstacle, gun, score, difficulty, sound, hit effects, raycaster)
    - drives game loop: input -> update -> render

### Engine layer (rendering and platform)
- engine/window.py
    - owns Pygame init, GL context init, swap, dt/fps, mouse capture/release
    - used by main.py

- engine/camera.py
    - owns yaw/pitch look vectors, movement clamps, view/projection matrices, ray direction
    - used by main.py

- engine/shader.py
    - loads and caches shader programs from shaders/*.vert + shaders/*.frag
    - used by main.py

- engine/mesh.py
    - defines GPU mesh primitives and VAOs: SphereMesh, BoxMesh, QuadMesh, SkyboxQuad
    - used by main.py

- engine/renderer.py
    - defines HUDRenderer for text and overlays
    - uses Pygame surfaces -> GL texture upload
    - used by main.py

### Game layer (logic and state)
- game/target.py
    - SphereTarget implementation and TargetManager
    - controls counts/sizes/speeds/pulse by difficulty
    - used by main.py and raycaster contract methods

- game/obstacle.py
    - blinking penalty targets
    - sphere penalty targets active from Hard difficulty onward
    - used by main.py

- game/raycaster.py
    - analytic ray-sphere intersections and closest-target selection
    - used by main.py

- game/gun.py
    - AK model geometry, recoil, ammo, reload timeline
    - used by main.py

- game/score.py
    - scoring, accuracy, streak, timer lifecycle
    - used by main.py

- game/difficulty.py
    - level progression from hit count
    - used by main.py

- game/hit_effect.py
    - hit marker and screen flash effects
    - used by main.py and rendered through HUDRenderer

- game/sound.py
    - loads fixed files game/sounds/shot_sound.mp3 and game/sounds/reload.mp3
    - generates procedural fallback sounds when files/mixer unavailable
    - used by main.py

- game/__init__.py, engine/__init__.py
    - package markers

## Shaders, .vert and .frag, and How Python Uses Them

A shader program is always a pair:
- .vert (vertex shader): transforms vertices
- .frag (fragment shader): computes final pixel color

Python side:
- main.py asks ShaderManager.load("phong"), load("skybox"), load("hud")
- ShaderManager reads shaders/phong.vert + shaders/phong.frag (etc), compiles, caches
- mesh VAOs bind to attributes expected by each shader
- render loop sets uniforms and draws meshes

### phong.vert + phong.frag

Files:
- shaders/phong.vert
- shaders/phong.frag

Used for:
- arena geometry panels
- sphere targets
- obstacles
- first-person gun

Important uniforms set from Python:
- m_model, m_view, m_proj
- light_pos, cam_pos
- object_color
- ambient_strength, specular_strength
- hit_flash
- stripe_mode (solid vs striped threat style)

### skybox.vert + skybox.frag

Files:
- shaders/skybox.vert
- shaders/skybox.frag

Used for:
- full-screen sky/space backdrop

Python usage:
- render first with depth disabled
- set uniform time for shimmer animation
- draw SkyboxQuad

### hud.vert + hud.frag

Files:
- shaders/hud.vert
- shaders/hud.frag

Used for:
- text HUD textures
- crosshair rectangles
- flash overlay
- vignette
- ready/pause/end overlays

Python usage:
- HUDRenderer builds Pygame surfaces for text
- uploads to GL texture
- toggles use_texture uniform
- draws full-screen quad or pixel-space rectangles

## Render Pipeline per Frame

From main.py render():
1. Clear color + depth
2. Skybox (depth disabled)
3. World panels
4. Obstacles
5. Targets
6. Gun in view-space (depth disabled so it stays visible)
7. HUD overlays (depth disabled)

## Gameplay Flow and Data Flow

Input flow:
- main.handle_events reads Pygame events
- camera.process_mouse updates look
- clicking calls shoot() unless paused/end state
- ESC pauses during gameplay, ESC on pause quits

Shot resolution flow:
1. gun.can_fire check
2. score.record_shot and gun.fire
3. optional auto reload sound if mag hits zero
4. raycaster finds closest target hit
5. obstacle intersections computed in same ray path
6. nearest valid hit wins:
     - obstacle hit: penalty
     - target hit: record hit + effects + difficulty update
     - no hit: miss effect

Update flow:
- camera movement (arena boundaries)
- targets update
- obstacles update (active only level >= 3)
- gun update (recoil + reload timeline)
- hit marker/flash update
- score timer update

## Modes and Difficulty

Mode:
- one arena mode with sphere targets

Difficulty progression:
- managed by DifficultyManager
- level increments every hits_per_level (default 8)
- level applies different target counts/speeds/sizes

Arena specifics (from game/target.py):
- sphere sizes, speeds, counts per level
- pulse enabled at higher levels

## Audio System

Primary assets:
- game/sounds/shot_sound.mp3
- game/sounds/reload.mp3

Behavior:
- shot sound plays on each valid shot
- reload sound plays on manual and auto reload start
- hit confirmation ping is procedural
- procedural fallback used if file missing or load fails

## HUD System Details

HUDRenderer:
- merges HUD text + ammo panel into one surface
- caches HUD state key to avoid unnecessary texture rebuilds
- throttles displayed FPS updates
- handles overlay screens:
    - ready screen
    - pause screen
    - end summary screen

## File-by-File Reference

### Root
- main.py: app entry point, game class, loop, input/update/render orchestration
- old_target.py: legacy target system not used by current runtime
- requirements.txt: Python dependencies

### engine/
- engine/window.py: window and GL context lifecycle, dt/fps, mouse grab state
- engine/camera.py: FPS camera math and arena movement constraints
- engine/shader.py: shader program load/cache/release
- engine/mesh.py: sphere/box/quad geometry and VAO wrappers
- engine/renderer.py: HUD drawing and overlay management
- engine/__init__.py: package marker

### game/
- game/target.py: target entities and target manager for both game modes
- game/obstacle.py: blinking sphere penalty targets
- game/raycaster.py: hit query math
- game/gun.py: weapon model, ammo/reload/recoil state machine
- game/score.py: score/accuracy/streak/timer model
- game/difficulty.py: level state model
- game/hit_effect.py: transient marker/flash effects
- game/sound.py: sound loading and fallback synthesis
- game/__init__.py: package marker

### shaders/
- shaders/phong.vert: world-space transform and normal transform
- shaders/phong.frag: phong lighting, stripe mode, hit flash
- shaders/skybox.vert: fullscreen position passthrough
- shaders/skybox.frag: gradient sky and star shimmer
- shaders/hud.vert: pixel-space transform for overlays
- shaders/hud.frag: textured or solid-color HUD fragments

## Common Customization Points

- Screen setup: main.py constants WIDTH, HEIGHT
- Round duration: main.py GAME_DURATION
- Arena dimensions: main.py ARENA_W/H/D
- Light placement: main.py LIGHT_POS
- Arena spawn bounds: game/target.py TargetManager bounds
- Difficulty pacing: game/difficulty.py hits_per_level
- Target behavior by level: game/target.py apply_difficulty
- Audio asset filenames: game/sound.py

## Notes

- This codebase currently contains some comment/text artifacts from prior automated edits. Runtime logic is unaffected, but cleanup can improve readability.
- If you want, the next improvement can be a code hygiene pass (docstrings/comments only) without touching gameplay behavior.
