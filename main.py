import os
import math
import random
import pygame
from os import listdir
from os.path import isfile, join # Dynamically load sprites from memory
pygame.init()

pygame.display.set_caption("Summer School Platformer")


WIDTH, HEIGHT = 1024, 600
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))

def flip(sprites):
	return [pygame.transform.flip(sprite, True, False) for sprite in sprites] # Flip on X, Don't Flip on Y

def loadSpriteSheets(dir1, dir2, width, height, direction = False):
	path = join("Sprites", dir1, dir2)
	images = [f for f in listdir(path) if isfile(join(path, f))]

	allSprites = {}

	for image in images:
		spriteSheet = pygame.image.load(join(path, image)).convert_alpha()

		sprites = []
		for i in range(spriteSheet.get_width() // width):
			surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
			rect = pygame.Rect(i * width, 0, width, height)
			surface.blit(spriteSheet, (0, 0), rect)
			sprites.append(pygame.transform.scale2x(surface))

		if direction:
			allSprites[image.replace(".png", "") + "_right"] = sprites
			allSprites[image.replace(".png", "") + "_left"] = flip(sprites)

		else:
			allSprites[image.replace(".png", "")] = sprites

	return allSprites

def loadBlock(size):
	path = join("Sprites", "Ground.png")
	image = pygame.image.load(path).convert_alpha()
	surface = pygame.Surface((size,size), pygame.SRCALPHA, 32)
	rect = pygame.Rect(6 * 64, 10 * 64, size, size)
	surface.blit(image, (0,0), rect)
	return surface

class Player(pygame.sprite.Sprite): # Sprites are easy for Pixel Perfect Collision
	COLOR = (255, 0, 0)
	GRAVITY = 1
	SPRITES = loadSpriteSheets("Players", "Blue", 32, 64, True)
	ANIMATION_DELAY = 10

	def __init__(self, x, y, width, height):
		super().__init__()
		self.rect = pygame.Rect(x, y, width, height)
		self.xVel = 0
		self.yVel = 0
		self.mask = None
		self.direction = "left"
		self.animationCount = 0
		self.fallTimer = 0
		self.jumpCount = 0
		self.health = 3
		self.coins = 0

	def jump(self):
		self.yVel = -self.GRAVITY * 8
		self.animationCount = 0
		self.jumpCount += 1
		if self.jumpCount == 1 or self.jumpCount == 2:
			self.fallTimer = 0 # Removing accumulated gravity to double jump

	def move(self, dx, dy):
		self.rect.x += dx
		self.rect.y += dy

	def moveLeft(self, vel): # (0,0) is the top left
		self.xVel = -vel
		if self.direction != "left":
			self.direction = "left"
			self.animationCount = 0

	def moveRight(self, vel):
		self.xVel = vel
		if self.direction != "right":
			self.direction = "right"
			self.animationCount = 0

	def landed(self):
		self.yVel = 0
		self.fallTimer = 0
		self.jumpCount = 0

	def hitHead(self):
		self.fallTimer = 0
		self.yVel *= -1

	def loop(self, fps): # Everything that needs to be updated each frame
		self.move(self.xVel, self.yVel)
		self.yVel += min(1, (self.fallTimer / fps) * self.GRAVITY)

		self.fallTimer += 1
		self.updateSprite()

	def updateSprite(self):
		spriteSheet = "Stand"
		if self.yVel < 0:
			spriteSheet = "Jump"
		elif self.xVel != 0:
			spriteSheet = "Walk"

		spriteSheetName = spriteSheet + "_" + self.direction
		sprites = self.SPRITES[spriteSheetName]
		spriteIndex = (self.animationCount // self.ANIMATION_DELAY) % len(sprites)
		self.sprite = sprites[spriteIndex]
		self.animationCount += 1
		self.update()

	def update(self): # Updates the collision rectangle
		self.rect = self.sprite.get_rect(topleft = (self.rect.x, self.rect.y))
		self.mask = pygame.mask.from_surface(self.sprite) # Accounts for transparent Pixels


	def draw(self, window, offsetX):
		window.blit(self.sprite, (self.rect.x - offsetX, self.rect.y))

class Object(pygame.sprite.Sprite):
	def __init__(self, x, y, width, height, name = None):
		super().__init__()
		self.rect = pygame.Rect(x, y, width, height)
		self.image = pygame.Surface((width, height), pygame.SRCALPHA)
		self.width = width
		self.height = height
		self.name = __name__

	def draw(self, window, offsetX):
		window.blit(self.image, (self.rect.x - offsetX, self.rect.y))


class Block(Object):
	def __init__(self, x, y, size):
		super().__init__(x, y, size, size) # Since Object constructor requires 4 args
		block = loadBlock(size)
		self.image.blit(block, (0,0))
		self.mask = pygame.mask.from_surface(self.image)


def veticalCollisionHandler(player, objects, dy): # Check vertical only if no horizontal collisions
	collidedObjects = []
	for obj in objects:
		if pygame.sprite.collide_mask(player, obj):
			if dy > 0:
				player.rect.bottom = obj.rect.top
				player.landed()
			elif dy < 0:
				player.rect.top = obj.rect.bottom - 28 # To account for the empty pixels
				player.hitHead()

		collidedObjects.append(obj)

	return collidedObjects

def horizontalCollisionHandler(player, objects, dx):
	player.move(dx, 0) # Moving the player to where they would be preemptively
	player.update() # To update the mask and check for collisions
	collidedObject = None
	for obj in objects:
		if pygame.sprite.collide_mask(player, obj): # Checking collisions
			collidedObject = obj
			break

	player.move(-dx, 0) # Reverting back the movement no matter if they collided or not
	player.update()
	return collidedObject

def movementHandler(player, objects):
	keys = pygame.key.get_pressed()

	player.xVel = 0 # Moves only when key is pressed
	collideLeft = horizontalCollisionHandler(player, objects, -PLAYER_VEL * 2) # Times 2 gives extra space between the player and the block to account for the 
	collideRight = horizontalCollisionHandler(player, objects, PLAYER_VEL * 2) # changing of the animation and to not cause any bugs since not all of the animations are the same size

	if keys[pygame.K_LEFT] and not collideLeft:
		player.moveLeft(PLAYER_VEL)
	if keys[pygame.K_RIGHT] and not collideRight:
		player.moveRight(PLAYER_VEL)

	veticalCollisionHandler(player, objects, player.yVel)



def getBackground(name):
	return pygame.image.load(join("Sprites", "Backgrounds", name))


def draw(window, bgImage, player, objects, offsetX):
	window.blit(bgImage, (0,0))

	for obj in objects:
		obj.draw(window, offsetX)

	player.draw(window, offsetX)

	pygame.display.update()

def main(window):
	clock = pygame.time.Clock()
	bgImage = getBackground("blue_desert.png")
	blockSize = 64

	player = Player(100, 100, 50, 50)
	floor = [Block(i * blockSize, HEIGHT - blockSize, blockSize) for i in range(-WIDTH // blockSize, (WIDTH * 2) // blockSize)]
	
	objects = [*floor, Block(0, HEIGHT - blockSize * 2, blockSize), Block(blockSize * 4, HEIGHT - blockSize * 5, blockSize)]

	offsetX = 0 
	scrollAreaWidth = 200 # Starts scrolling once a point is reached to the left or right

	run = True
	while run: # Regulates the FPS at 60 (Max)
		clock.tick(FPS)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				run = False
				break

			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_SPACE and player.jumpCount < 3:
					player.jump() 

		player.loop(FPS)
		movementHandler(player, objects)		
		draw(window, bgImage, player, objects, offsetX)

		if (player.rect.right - offsetX >= WIDTH - scrollAreaWidth and player.xVel > 0) or (player.rect.left - offsetX <= scrollAreaWidth and player.xVel < 0):
			offsetX += player.xVel

	pygame.quit()
	quit()


if __name__ == "__main__": # Calls the main function only if the file is run directly
	main(window)
