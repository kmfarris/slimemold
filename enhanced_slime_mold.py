import pygame
import numpy as np
import random
from noise import snoise2
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict

class Species(Enum):
    PHYSARUM = 1
    DICTYOSTELIUM = 2
    FULIGO = 3

@dataclass
class Particle:
    x: float
    y: float
    angle: float
    speed: float
    species: Species
    energy: float
    moisture_preference: float
    temperature_preference: float
    trail_strength: float
    sensor_distance: float
    sensor_angle: float
    rotation_angle: float

class Environment:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.temperature_map = np.zeros((width, height))
        self.moisture_map = np.zeros((width, height))
        self.obstacle_map = np.zeros((width, height))
        self.food_map = np.zeros((width, height))
        self.pheromone_map = np.zeros((width, height))
        self.pheromone_decay_rate = 0.99
        self.temperature_change_rate = 0.1
        self.moisture_change_rate = 0.05
        self.generate_environment()

    def generate_environment(self):
        # Generate temperature variations
        scale = 0.02
        for x in range(self.width):
            for y in range(self.height):
                self.temperature_map[x, y] = snoise2(x * scale, y * scale, octaves=3) * 10 + 20  # 20°C ± 10°C
                self.moisture_map[x, y] = snoise2(x * scale + 1000, y * scale + 1000, octaves=3) * 0.5 + 0.5
                
                # Generate obstacles
                if snoise2(x * scale + 2000, y * scale + 2000, octaves=2) > 0.7:
                    self.obstacle_map[x, y] = 1.0
                
                # Generate more food sources
                if snoise2(x * scale + 3000, y * scale + 3000, octaves=4) > 0.5:  # Lowered threshold
                    self.food_map[x, y] = 1.0

    def update(self):
        # Decay pheromones
        self.pheromone_map *= self.pheromone_decay_rate
        # Update temperature and moisture (simulate day/night cycle)
        time = pygame.time.get_ticks() / 1000
        self.temperature_map += np.sin(time / 60) * self.temperature_change_rate
        self.moisture_map += np.cos(time / 60) * self.moisture_change_rate

class SlimeMold:
    def __init__(self, width: int, height: int, simulator=None):
        self.width = width
        self.height = height
        self.particles: List[Particle] = []
        self.environment = Environment(width, height)
        self.simulator = simulator  # Store simulator reference
        
        # Define species parameters
        self.species_params = {
            Species.PHYSARUM: {
                'speed': 1.0,
                'sensor_distance': 9,
                'trail_strength': 1.0,
                'moisture_pref': 0.7,
                'temp_pref': 25.0,
                'count': 200
            },
            Species.DICTYOSTELIUM: {
                'speed': 1.5,
                'sensor_distance': 7,
                'trail_strength': 0.8,
                'moisture_pref': 0.8,
                'temp_pref': 22.0,
                'count': 200
            },
            Species.FULIGO: {
                'speed': 0.8,
                'sensor_distance': 11,
                'trail_strength': 1.2,
                'moisture_pref': 0.6,
                'temp_pref': 20.0,
                'count': 200
            }
        }
        
        self.initialize_particles()
        
    def initialize_particles(self):
        for species in Species:
            params = self.species_params[species]
            for _ in range(params['count']):
                # Start particles in a tighter group in the center
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(0, 50)  # Tighter initial group
                x = self.width // 2 + radius * math.cos(angle)
                y = self.height // 2 + radius * math.sin(angle)
                
                self.particles.append(Particle(
                    x=x,
                    y=y,
                    angle=random.uniform(0, 2 * math.pi),
                    speed=params['speed'],
                    species=species,
                    energy=100.0,
                    moisture_preference=params['moisture_pref'],
                    temperature_preference=params['temp_pref'],
                    trail_strength=params['trail_strength'],
                    sensor_distance=params['sensor_distance'],
                    sensor_angle=math.pi / 4,
                    rotation_angle=math.pi / 8
                ))

    def update(self):
        for particle in self.particles:
            # Get environmental conditions at particle position
            x, y = int(particle.x), int(particle.y)
            temperature = self.environment.temperature_map[x, y]
            moisture = self.environment.moisture_map[x, y]
            
            # Adjust behavior based on environmental conditions
            temp_diff = abs(temperature - particle.temperature_preference)
            moisture_diff = abs(moisture - particle.moisture_preference)
            
            # Calculate environmental stress
            stress = (temp_diff / 10) + moisture_diff
            particle.speed = max(0.1, particle.speed * (1 - stress * 0.1))
            
            # Sensor positions - increase sensor distance when energy is low
            sensor_dist = particle.sensor_distance * (1.0 + (100.0 - particle.energy) / 50.0)
            front_x = particle.x + sensor_dist * math.cos(particle.angle)
            front_y = particle.y + sensor_dist * math.sin(particle.angle)
            
            left_x = particle.x + sensor_dist * math.cos(particle.angle - particle.sensor_angle)
            left_y = particle.y + sensor_dist * math.sin(particle.angle - particle.sensor_angle)
            
            right_x = particle.x + sensor_dist * math.cos(particle.angle + particle.sensor_angle)
            right_y = particle.y + sensor_dist * math.sin(particle.angle + particle.sensor_angle)
            
            # Get sensor values
            front_val = self.get_sensor_value(front_x, front_y, particle)
            left_val = self.get_sensor_value(left_x, left_y, particle)
            right_val = self.get_sensor_value(right_x, right_y, particle)
            
            # Decision making with species-specific behavior
            if particle.species == Species.PHYSARUM:
                # Physarum follows strong trails and food
                if front_val > left_val and front_val > right_val:
                    pass
                elif left_val > right_val:
                    particle.angle -= particle.rotation_angle
                else:
                    particle.angle += particle.rotation_angle
            elif particle.species == Species.DICTYOSTELIUM:
                # Dictyostelium is more exploratory
                if random.random() < 0.1:  # Occasional random turns
                    particle.angle += random.uniform(-math.pi/4, math.pi/4)
                elif front_val > left_val and front_val > right_val:
                    pass
                elif left_val > right_val:
                    particle.angle -= particle.rotation_angle
                else:
                    particle.angle += particle.rotation_angle
            else:  # FULIGO
                # Fuligo is cautious but follows food
                if front_val > left_val and front_val > right_val:
                    pass
                elif left_val > right_val:
                    particle.angle -= particle.rotation_angle * 0.5
                else:
                    particle.angle += particle.rotation_angle * 0.5
            
            # Move particle
            new_x = particle.x + particle.speed * math.cos(particle.angle)
            new_y = particle.y + particle.speed * math.sin(particle.angle)
            
            # Check for obstacles
            if not self.is_obstacle(new_x, new_y):
                particle.x = new_x
                particle.y = new_y
            else:
                # Bounce off obstacles
                particle.angle += math.pi
            
            # Wrap around screen
            particle.x %= self.width
            particle.y %= self.height
            
            # Update trail map (stronger trails for better cohesion)
            x, y = int(particle.x), int(particle.y)
            if 0 <= x < self.width and 0 <= y < self.height:
                self.environment.pheromone_map[x, y] = min(1.0, 
                    self.environment.pheromone_map[x, y] + particle.trail_strength)
            
            # Get time scale for speed adjustments
            time_scale = 1.0
            if self.simulator:
                time_scale = self.simulator.speed_settings[self.simulator.current_speed]['simulation_speed']
            
            # Consume food and update energy
            if self.environment.food_map[x, y] > 0:
                # Consume food more aggressively
                consumption_rate = 0.5  # Much higher consumption rate
                energy_gain = 20.0  # Much higher energy gain
                particle.energy = min(100.0, particle.energy + energy_gain)
                self.environment.food_map[x, y] = max(0, self.environment.food_map[x, y] - consumption_rate)
            
            # Decrease energy over time (slower when not moving)
            movement_factor = 1.0 if abs(particle.speed) > 0.1 else 0.5
            # Energy consumption is now independent of time_scale to prevent rapid death at high speeds
            particle.energy -= 0.005 * movement_factor
            
            # Reproduce if energy is high (adjusted for speed)
            if particle.energy > 80 and random.random() < 0.001 * time_scale:
                self.particles.append(Particle(
                    x=particle.x,
                    y=particle.y,
                    angle=random.uniform(0, 2 * math.pi),
                    speed=particle.speed,
                    species=particle.species,
                    energy=50.0,
                    moisture_preference=particle.moisture_preference,
                    temperature_preference=particle.temperature_preference,
                    trail_strength=particle.trail_strength,
                    sensor_distance=particle.sensor_distance,
                    sensor_angle=particle.sensor_angle,
                    rotation_angle=particle.rotation_angle
                ))
                particle.energy -= 30  # Reduced energy cost for reproduction

        # Update environment
        self.environment.update()
        
        # Remove dead particles
        self.particles = [p for p in self.particles if p.energy > 0]

    def get_sensor_value(self, x: float, y: float, particle: Particle) -> float:
        x = int(x) % self.width
        y = int(y) % self.height
        if self.is_obstacle(x, y):
            return -1.0
        
        # Food is the primary attractant
        food_value = self.environment.food_map[x, y]
        if food_value > 0:
            # Make food extremely attractive, especially when hungry
            hunger_factor = 1.0 + (100.0 - particle.energy) / 20.0
            return food_value * 100.0 * hunger_factor
        
        # Pheromones are secondary
        pheromone_value = self.environment.pheromone_map[x, y]
        return pheromone_value * 0.5  # Moderate trail following

    def is_obstacle(self, x: float, y: float) -> bool:
        x = int(x) % self.width
        y = int(y) % self.height
        return self.environment.obstacle_map[x, y] > 0.5

class SlimeMoldSimulator:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Enhanced Slime Mold Simulator")
        self.clock = pygame.time.Clock()
        self.slime_mold = SlimeMold(width, height, simulator=self)
        self.running = True
        self.paused = False
        self.show_debug = False
        
        # Create debug surfaces
        self.debug_surface = pygame.Surface((width, height))
        self.debug_surface.set_alpha(128)  # Semi-transparent
        
        # Initialize active species
        self.active_species = {
            Species.PHYSARUM: True,
            Species.DICTYOSTELIUM: True,
            Species.FULIGO: True
        }
        
        # Initialize speed settings with more dramatic differences
        self.speed_settings = {
            'normal': {'fps': 60, 'simulation_speed': 1.0, 'name': 'Normal'},
            'fast': {'fps': 60, 'simulation_speed': 3.0, 'name': 'Fast'},
            'supaslime': {'fps': 60, 'simulation_speed': 6.0, 'name': 'Supaslime!'}
        }
        self.current_speed = 'normal'
        self.update_simulation_speed()

    def update_simulation_speed(self):
        # Update particle speeds and other time-dependent parameters
        speed_factor = self.speed_settings[self.current_speed]['simulation_speed']
        
        # Update particle speeds
        for particle in self.slime_mold.particles:
            base_speed = self.slime_mold.species_params[particle.species]['speed']
            particle.speed = base_speed * speed_factor
            # Also adjust sensor distance based on speed
            particle.sensor_distance = self.slime_mold.species_params[particle.species]['sensor_distance'] * (1 + (speed_factor - 1) * 0.5)
        
        # Update environment parameters
        self.slime_mold.environment.pheromone_decay_rate = 0.99 ** (1/speed_factor)
        self.slime_mold.environment.temperature_change_rate = 0.1 * speed_factor
        self.slime_mold.environment.moisture_change_rate = 0.05 * speed_factor

    def run(self):
        last_time = pygame.time.get_ticks()
        while self.running:
            current_time = pygame.time.get_ticks()
            delta_time = (current_time - last_time) / 1000.0  # Convert to seconds
            last_time = current_time
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_d:
                        self.show_debug = not self.show_debug
                    elif event.key == pygame.K_f:
                        x, y = pygame.mouse.get_pos()
                        self.slime_mold.environment.food_map[x, y] = 1.0
                    elif event.key == pygame.K_1:
                        self.toggle_species(Species.PHYSARUM)
                    elif event.key == pygame.K_2:
                        self.toggle_species(Species.DICTYOSTELIUM)
                    elif event.key == pygame.K_3:
                        self.toggle_species(Species.FULIGO)
                    elif event.key == pygame.K_r:
                        self.reset_simulation()
                    elif event.key == pygame.K_s:
                        # Cycle through speed settings
                        speeds = list(self.speed_settings.keys())
                        current_index = speeds.index(self.current_speed)
                        self.current_speed = speeds[(current_index + 1) % len(speeds)]
                        self.update_simulation_speed()

            if not self.paused:
                # Update simulation multiple times per frame based on speed
                speed_factor = self.speed_settings[self.current_speed]['simulation_speed']
                num_updates = max(1, int(speed_factor))
                for _ in range(num_updates):
                    self.slime_mold.update()

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)  # Keep FPS constant at 60

        pygame.quit()

    def toggle_species(self, species: Species):
        self.active_species[species] = not self.active_species[species]
        # Remove particles of inactive species
        self.slime_mold.particles = [p for p in self.slime_mold.particles if self.active_species[p.species]]
        # Add particles for newly active species
        if self.active_species[species]:
            params = self.slime_mold.species_params[species]
            for _ in range(params['count']):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(0, 50)
                x = self.slime_mold.width // 2 + radius * math.cos(angle)
                y = self.slime_mold.height // 2 + radius * math.sin(angle)
                
                self.slime_mold.particles.append(Particle(
                    x=x,
                    y=y,
                    angle=random.uniform(0, 2 * math.pi),
                    speed=params['speed'],
                    species=species,
                    energy=100.0,
                    moisture_preference=params['moisture_pref'],
                    temperature_preference=params['temp_pref'],
                    trail_strength=params['trail_strength'],
                    sensor_distance=params['sensor_distance'],
                    sensor_angle=math.pi / 4,
                    rotation_angle=math.pi / 8
                ))

    def reset_simulation(self):
        # Reset all particles
        self.slime_mold.particles = []
        # Reinitialize only active species
        for species in Species:
            if self.active_species[species]:
                params = self.slime_mold.species_params[species]
                for _ in range(params['count']):
                    angle = random.uniform(0, 2 * math.pi)
                    radius = random.uniform(0, 50)
                    x = self.slime_mold.width // 2 + radius * math.cos(angle)
                    y = self.slime_mold.height // 2 + radius * math.sin(angle)
                    
                    self.slime_mold.particles.append(Particle(
                        x=x,
                        y=y,
                        angle=random.uniform(0, 2 * math.pi),
                        speed=params['speed'],
                        species=species,
                        energy=100.0,
                        moisture_preference=params['moisture_pref'],
                        temperature_preference=params['temp_pref'],
                        trail_strength=params['trail_strength'],
                        sensor_distance=params['sensor_distance'],
                        sensor_angle=math.pi / 4,
                        rotation_angle=math.pi / 8
                    ))

    def draw(self):
        self.screen.fill((0, 0, 0))
        
        if self.show_debug:
            # Clear debug surface
            self.debug_surface.fill((0, 0, 0, 0))
            
            # Draw temperature map with reduced resolution
            for x in range(0, self.slime_mold.width, 4):
                for y in range(0, self.slime_mold.height, 4):
                    temp = self.slime_mold.environment.temperature_map[x, y]
                    # Ensure color values are integers and within valid range
                    r = min(255, max(0, int(temp * 10)))
                    b = min(255, max(0, 255 - int(temp * 10)))
                    pygame.draw.rect(self.debug_surface, (r, 0, b), (x, y, 4, 4))
            
            # Draw moisture map with reduced resolution
            for x in range(0, self.slime_mold.width, 4):
                for y in range(0, self.slime_mold.height, 4):
                    moisture = self.slime_mold.environment.moisture_map[x, y]
                    alpha = min(255, max(0, int(moisture * 50)))
                    pygame.draw.rect(self.debug_surface, (0, 0, 255, alpha), (x, y, 4, 4))
            
            self.screen.blit(self.debug_surface, (0, 0))
        
        # Draw obstacles with reduced resolution
        for x in range(0, self.slime_mold.width, 2):
            for y in range(0, self.slime_mold.height, 2):
                if self.slime_mold.environment.obstacle_map[x, y] > 0.5:
                    pygame.draw.rect(self.screen, (100, 100, 100), (x, y, 2, 2))
        
        # Draw food sources with reduced resolution
        for x in range(0, self.slime_mold.width, 2):
            for y in range(0, self.slime_mold.height, 2):
                if self.slime_mold.environment.food_map[x, y] > 0:
                    pygame.draw.rect(self.screen, (0, 255, 0), (x, y, 2, 2))
        
        # Draw particles
        species_colors = {
            Species.PHYSARUM: (255, 255, 255),
            Species.DICTYOSTELIUM: (255, 200, 200),
            Species.FULIGO: (200, 200, 255)
        }
        
        for particle in self.slime_mold.particles:
            if self.active_species[particle.species]:
                color = species_colors[particle.species]
                energy_factor = particle.energy / 100.0
                color = tuple(int(c * energy_factor) for c in color)
                pygame.draw.circle(self.screen, color, (int(particle.x), int(particle.y)), 1)
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        text = font.render(f"Particles: {len(self.slime_mold.particles)}", True, (255, 255, 255))
        self.screen.blit(text, (10, 10))
        
        # Draw species status
        y_offset = 50
        for species in Species:
            status = "ON" if self.active_species[species] else "OFF"
            color = (0, 255, 0) if self.active_species[species] else (255, 0, 0)
            text = font.render(f"{species.name}: {status}", True, color)
            self.screen.blit(text, (10, y_offset))
            y_offset += 30
        
        # Draw speed status
        speed_color = (255, 255, 0)  # Yellow
        text = font.render(f"Speed: {self.speed_settings[self.current_speed]['name']}", True, speed_color)
        self.screen.blit(text, (10, y_offset))
        
        if self.paused:
            text = font.render("PAUSED", True, (255, 0, 0))
            self.screen.blit(text, (self.slime_mold.width - 100, 10))
        
        if self.show_debug:
            text = font.render("DEBUG MODE", True, (0, 255, 0))
            self.screen.blit(text, (10, self.slime_mold.height - 40))

if __name__ == "__main__":
    simulator = SlimeMoldSimulator()
    simulator.run() 