# neat-learns-to-drift

I started this thinking that it'd be a fun project to do over a week or so that'd also probably look good on a résumé. Instead, it devolved into a month of pain and suffering that eventually resulted in this pile of spaghetti code. It trains (or at least, attempts to train) an neural network to play a small, top-down driving game, which ended up taking significantly longer to make than it should have (as it turns out, drift physics are *really* hard to get right).

If you run this yourself (go read the Dependencies section if you decide to), there's actually 3 different files you can run: `main`, `main-slow`, and `trackbuilder`. 

`trackbuilder` is something I wrote so I could build tracks for the AI to drive on, and decided to leave in here in case you want to make your own. The controls aren't explained anywhere, but they're pretty simple: left click to place the corners of the track (right click to remove the last corner you placed). Once you've placed the corners, press enter, then click to place the start point once it's where you want it. Then you add just need to add checkpoints, which you do with left click. There's no required number of checkpoints, but it's best to have a lot of them, especially at sharp corners. You also don't have to place them in any order, but the AI cars will spawn facing toward the first one you place, so put that one in front of the start point. Once you've placed checkpoints, press enter and the program will save the track before closing.

`main` and `main-slow` both do the same AI training, just in slightly different methods. `main` has every network in a population play the game at the same time. This means training is *much* faster, but it also requires a lot more computing power. If your computer can't handle that, `main-slow` has networks play the game one at a time, which is much easier on your processer but also massively increases training time.

### The Neural Network

I'm training this neural network using an algorithim called NEAT (NeuroEvolution of Augmenting Topologies), which trains the network by simulating natural selection. It begins by creating a population of neural networks that are all slightly different, then has them all play the game until they die (either because they hit a wall or they stop moving). As the networks play the game, they're assigned a fitness value based on how far they drive, as well as how fast they drive. Once all the networks have died, the ones with the highest fitness "reproduce" by creating a new population of networks that combine their characteristics, and then "mutate" the new population by making slight changes to each of the networks in it. This process is then repeated until a "perfect" network that never dies is created. The actual process is a lot more complex than that, but I won't go into the details here (mainly because I don't actually know any of the details).


### Dependencies

If you want to run this yourself, you'll need the latest version of python (obviously), which you can download from the [official website](https://www.python.org/downloads/) if you don't already have it. On top of python itself, there's a few other things you'll also need:
- If you've never used python before, you'll want VS Code so you can install packages (don't worry, it's not hard) and maybe mess around with the code a bit. Just follow [this tutorial](https://code.visualstudio.com/docs/python/python-tutorial) to get it set up.
- There's also a few external packages I've used to make my life easier that you'll need:
  - NEAT (`pip install neat-python`): This is the library for creating and training the neural networks. Once you set it up and point it at the config file, the networks themselves are pretty much just big black boxes - give them inputs, they give you outputs - and the only things you have to do with them is assign fitness values, and kill them when they crash their car.
  - Pygame (`pip install pygame`): Pygame is designed for making games, but it's also *incredibly* useful for graphics in general.
  - Shapely (`pip install shapely`): Shapely has a ton of functions for doing complex geometry operations. Most of those functions are useless here, but it makes raycasting and collision detection relatively trivial.
  - ConfigObj (`pip install configobj`): Python does have its own built-in library for reading config files, but I've always used ConfigObj instead. It's a bit more complicated, but it has more features and (more importantly) supports subsections in config files. Speaking of config files...
 
 ### The Config Files
 
 There are two config files in here: `config.txt` and `neat_config.txt`. `neat_config.txt` is the config for the NEAT algorithm. Don't touch it unless you know what you're doing. `config.txt` is the config file for everything else - car physics, AI training, display colors, *everything*. I've done my best to explain what each item inside it does, and I encourage you to mess with it!

PS: Both accounts making commits to this (AllTheNamesAreTaken and JustASideQuestNPC) are mine. AllTheNamesAreTaken is my personal one and JustASideQuestNPC is my "professional" one, and I've had some issues getting VS Code to use the correct one.
