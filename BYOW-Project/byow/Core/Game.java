package byow.Core;

import byow.InputDemo.InputSource;
import byow.TileEngine.TERenderer;
import byow.TileEngine.TETile;
import byow.TileEngine.Tileset;
import edu.princeton.cs.algs4.In;
import edu.princeton.cs.algs4.StdDraw;

import java.awt.*;
import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Random;

import static byow.Core.Engine.WIDTH;
import static byow.Core.Engine.HEIGHT;

public class Game {

    public static String seed;
    public TETile[][] world;
    private Position randomAv;
    private Position lockedDoorPos;
    public static boolean playingGame;
    public boolean inMainWorld = true;
    public Position oldWorldAvatarPosition;
    public Random myRand;

    public Game() {
        seed = "";
    }

    public TETile[][] startScreen(InputSource input) {
        String seed1 = "";
        char getstart = input.getNextKey();
        if (getstart == 'n' || getstart == 'N') {
            returnSeed(seed1);
        }
        if (getstart == 'L' || getstart == 'l') {
            In file = new In("game.txt");
            String[] line = file.readLine().split(" ");
            seed1 = line[0];
            // returnSeed(seed1);
        } else {
            while (input.possibleNextInput()) {
                char current = input.getNextKey();
                if (current == 'S' || current == 's') {
                    returnSeed(seed1);
                    break;
                }
                seed1 += current;
                returnSeed(seed1);
            }
        }
        myRand = new Random(Long.parseLong(seed1));
        seed = seed1;
        WorldGenerator x = new WorldGenerator();
        world = x.returnWorld();
        ArrayList<Position> floorTile = x.chooseRandomFloor();
        int randomClosetIndex = myRand.nextInt(floorTile.size());
        lockedDoorPos = floorTile.get(randomClosetIndex);
        if (getstart != 'l' && getstart != 'L') {
            // Random rand = new Random();
            int randomIndex = myRand.nextInt(floorTile.size());
            randomAv = floorTile.get(randomIndex);
            world[randomAv.x][randomAv.y] = Tileset.AVATAR;
            world[lockedDoorPos.x][lockedDoorPos.y] = Tileset.LOCKED_DOOR;

        } else {
            In file = new In("game.txt");
            String[] line = file.readLine().split(" ");
            int randomAvx = Integer.parseInt(line[1]);
            int randomAvy = Integer.parseInt(line[2]);
            int unlockedOrLocked = Integer.parseInt(line[3]);
            int randomLoX = Integer.parseInt(line[4]);
            int randomLoY = Integer.parseInt(line[5]);
            world[randomAvx][randomAvy] = Tileset.AVATAR;
            if (unlockedOrLocked==1) {
                world[randomLoX][randomLoY] = Tileset.LOCKED_DOOR;
            }else{
                world[randomLoX][randomLoY] = Tileset.UNLOCKED_DOOR;
            }
            randomAv = new Position(randomAvx, randomAvy);
        }
        TERenderer ter = new TERenderer();
        ter.initialize(WIDTH, HEIGHT + 2);
        ter.renderFrame(world);
        playingGame = true;
        // hudDisplay(myMouse(), getTime(), world);
        //hudDisplay(myMouse(), getTime(), world);
        playingGame = gameMoves(world, randomAv, input);
        if (!playingGame) {
            return world;
        }
        return world;
    }

    private Position myMouse() {
        int x = (int) StdDraw.mouseX();
        int y = (int) StdDraw.mouseY();
        return new Position(Math.min(x, WIDTH - 1), Math.min(y, HEIGHT - 1));
    }

    private String getTime() {
        Calendar calendar = Calendar.getInstance();
        java.util.Date date = calendar.getTime();
        return new SimpleDateFormat("MM-dd-yyyy HH:mm:ss").format(date);
    }

    public void startScreen() {
        StdDraw.setCanvasSize(WIDTH * 16, HEIGHT * 16);
        Font font = new Font("Comic Sans", Font.BOLD, 30);
        StdDraw.setFont(font);
        StdDraw.setXscale(0, WIDTH);
        StdDraw.setYscale(0, HEIGHT);
        StdDraw.clear(Color.BLACK);
        StdDraw.clear(Color.BLACK);
        StdDraw.setPenColor(Color.WHITE);
        Font title = new Font("Comic Sans", Font.BOLD, 40);
        StdDraw.setFont(title);
        StdDraw.text(WIDTH / 2, HEIGHT * 15 / 20, "61B: THE GAME");
        Font menu = new Font("Comic Sans", Font.BOLD, 15);
        StdDraw.setFont(menu);
        StdDraw.text(WIDTH / 2, HEIGHT * 12 / 20, "New Game (N)");
        StdDraw.text(WIDTH / 2, HEIGHT * 10 / 20, "Load Game (L)");
        StdDraw.text(WIDTH / 2, HEIGHT * 8 / 20, "Quit (Q)");
        StdDraw.show();
    }

    private void returnSeed(String mySeed) {
        Font fnt = new Font("Comic Sans", Font.BOLD, 30);
        StdDraw.setFont(fnt);
        StdDraw.setXscale(0, WIDTH);
        StdDraw.setYscale(0, HEIGHT);
        StdDraw.clear(Color.BLACK);
        StdDraw.clear(Color.BLACK);
        StdDraw.setPenColor(Color.WHITE);
        Font fntseed = new Font("Comic Sans", Font.BOLD, 20);
        StdDraw.setFont(fntseed);
        // StdDraw.text(WIDTH / 2, HEIGHT * 15 / 20, "Insert your seed in me hehe;)?");
        StdDraw.text(WIDTH / 2, HEIGHT * 15 / 20, "Enter seed then press 's'.");
        StdDraw.text(WIDTH / 2, HEIGHT * 10 / 20, mySeed);
        StdDraw.setFont(fntseed);
        StdDraw.show();
    }

    private void endTheGame() {
        StdDraw.setCanvasSize(WIDTH * 16, HEIGHT * 16);
        Font font = new Font("Comic Sans", Font.BOLD, 20);
        StdDraw.setFont(font);
        StdDraw.setXscale(0, WIDTH);
        StdDraw.setYscale(0, HEIGHT);
        StdDraw.clear(Color.BLACK);
        StdDraw.clear(Color.BLACK);
        StdDraw.setPenColor(Color.WHITE);

        Font title = new Font("Comic Sans", Font.BOLD, 40);
        StdDraw.setFont(title);
        StdDraw.text(WIDTH / 2, HEIGHT * 15 / 20, "GAME OVER! ");
        Font menu = new Font("Comic Sans", Font.BOLD, 20);
        StdDraw.setFont(menu);
        StdDraw.text(WIDTH / 2, HEIGHT * 10 / 20, "Press L to load this game at the beginning of the next game.");
        StdDraw.show();
    }

    private void hudDisplay(Position position, String today, TETile[][] world) {
        StdDraw.setPenColor(Color.WHITE);
        Font hudDisplay = new Font("Comic Sans", Font.BOLD, 20);
        StdDraw.setFont(hudDisplay);
        StdDraw.textRight(WIDTH, HEIGHT + 1, world[position.x][position.y].description());
        StdDraw.textLeft(0, HEIGHT + 1, today);
        StdDraw.show();
    }

    public boolean gameMoves(TETile[][] world, Position y, InputSource source) {
        boolean lockedORUnlocked = true;
        //interact with the world
        while (source.possibleNextInput()) {
            Position avPos = y;
            char x = source.getNextKey();
            if (x == 'w' || x == 'W') {
                //find current position of avatar
                Position avPosNew = new Position(avPos.x, avPos.y + 1);
                if (world[avPosNew.x][avPosNew.y] == Tileset.WALL || world[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    TERenderer ter = new TERenderer();
                    ter.renderFrame(world);
                } else if (avPos.x == lockedDoorPos.x && avPos.y == lockedDoorPos.y){
                    if (lockedORUnlocked){
                        world[avPos.x][avPos.y] = Tileset.LOCKED_DOOR;
                    }else{
                        world[avPos.x][avPos.y] = Tileset.UNLOCKED_DOOR;
                    }
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                } else{
                    world[avPos.x][avPos.y] = Tileset.FLOOR;
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                }
            }
            if (x == 's' || x == 'S') {
                Position avPosNew = new Position(avPos.x, avPos.y - 1);
                if (world[avPosNew.x][avPosNew.y] == Tileset.WALL || world[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    TERenderer ter = new TERenderer();
                    ter.renderFrame(world);
                } else if (avPos.x == lockedDoorPos.x && avPos.y == lockedDoorPos.y){
                    if (lockedORUnlocked){
                        world[avPos.x][avPos.y] = Tileset.LOCKED_DOOR;
                    }else{
                        world[avPos.x][avPos.y] = Tileset.UNLOCKED_DOOR;
                    }
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                } else{
                    world[avPos.x][avPos.y] = Tileset.FLOOR;
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                }
            }
            if (x == 'a' || x == 'A') {
                Position avPosNew = new Position(avPos.x - 1, avPos.y);
                if (world[avPosNew.x][avPosNew.y] == Tileset.WALL || world[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    TERenderer ter = new TERenderer();
                    ter.renderFrame(world);
                } else if (avPos.x == lockedDoorPos.x && avPos.y == lockedDoorPos.y){
                    if (lockedORUnlocked){
                        world[avPos.x][avPos.y] = Tileset.LOCKED_DOOR;
                    }else{
                        world[avPos.x][avPos.y] = Tileset.UNLOCKED_DOOR;
                    }
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                } else{
                    world[avPos.x][avPos.y] = Tileset.FLOOR;
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                }
            }
            if (x == 'd' || x == 'D') {
                Position avPosNew = new Position(avPos.x + 1, avPos.y);
                if (world[avPosNew.x][avPosNew.y] == Tileset.WALL || world[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    TERenderer ter = new TERenderer();
                    ter.renderFrame(world);
                } else if (avPos.x == lockedDoorPos.x && avPos.y == lockedDoorPos.y){
                    if (lockedORUnlocked){
                        world[avPos.x][avPos.y] = Tileset.LOCKED_DOOR;
                    }else{
                        world[avPos.x][avPos.y] = Tileset.UNLOCKED_DOOR;
                    }
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                } else{
                    world[avPos.x][avPos.y] = Tileset.FLOOR;
                    world[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                }
            }
            if (x == 'o' || x == 'O') {
                NewCloset1 myCloset = new NewCloset1();
                TETile[][] newWorld;
                if (world[avPos.x + 1][avPos.y] == Tileset.LOCKED_DOOR || world[avPos.x - 1][avPos.y] == Tileset.LOCKED_DOOR || world[avPos.x][avPos.y + 1] == Tileset.LOCKED_DOOR || world[avPos.x][avPos.y - 1] == Tileset.LOCKED_DOOR) {
                    if (inMainWorld) {
                        newWorld = myCloset.returnClosetWorld();
                        oldWorldAvatarPosition = new Position(avPos.x, avPos.y);
                        ArrayList<Position> floorTile = myCloset.floorArray();
                        Random randOne = new Random(4);
                        int randomIndex = randOne.nextInt(floorTile.size());
                        Position randomAv = floorTile.get(randomIndex);
                        newWorld[randomAv.x][randomAv.y] = Tileset.AVATAR;
                        avPos.x = randomAv.x;
                        avPos.y = randomAv.y;
                        newWorld[avPos.x][avPos.y] = Tileset.AVATAR;
                        hudDisplay(myMouse(), getTime(), newWorld);
                        Random randTwo = new Random(6);
                        int randomIndexTwo = randTwo.nextInt(floorTile.size());
                        Position exitPos = floorTile.get(randomIndexTwo);
                        newWorld[exitPos.x][exitPos.y] = Tileset.LOCKED_DOOR;
                        TERenderer ter = new TERenderer();
                        ter.initialize(WIDTH, HEIGHT + 2);
                        ter.renderFrame(newWorld);
                        hudDisplay(myMouse(), getTime(), newWorld);
                        getInputOpen(newWorld, source, avPos);
                        lockedORUnlocked = false;
                    } else {
                        continue;
                    }

                }
            }
            if (x == 'c' || x == 'C'){
                if (world[avPos.x + 1][avPos.y] == Tileset.UNLOCKED_DOOR){
                    world[avPos.x + 1][avPos.y] = Tileset.LOCKED_DOOR;
                } else if (world[avPos.x - 1][avPos.y] == Tileset.UNLOCKED_DOOR){
                    world[avPos.x - 1][avPos.y] = Tileset.LOCKED_DOOR;
                } else if (world[avPos.x][avPos.y + 1] == Tileset.UNLOCKED_DOOR){
                    world[avPos.x][avPos.y + 1] = Tileset.LOCKED_DOOR;
                } else if (world[avPos.x][avPos.y - 1] == Tileset.UNLOCKED_DOOR){
                    world[avPos.x][avPos.y - 1] = Tileset.LOCKED_DOOR;
                }else{
                    continue;
                }
            }
            if (x == ':') {
                char next = source.getNextKey();
                if (next == 'q' || next == 'Q') {
                    endTheGame();
                    saveGame();
                    playingGame = false;
                    return playingGame;
                }
            }
            TERenderer ter = new TERenderer();
            ter.renderFrame(world);
            hudDisplay(myMouse(), getTime(), world);
        }
        return playingGame;
    }


    public void getInputOpen(TETile[][] newWorld, InputSource source, Position avPos) {
        TERenderer ter = new TERenderer();
        while (source.possibleNextInput()) {
            char openKey = source.getNextKey();
            if (openKey == 'w' || openKey == 'W') {
                //find current position of avatar
                Position avPosNew = new Position(avPos.x, avPos.y + 1);
                if (newWorld[avPosNew.x][avPosNew.y] == Tileset.WALL || newWorld[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    ter.renderFrame(newWorld);
                } else {
                    newWorld[avPos.x][avPos.y] = Tileset.FLOOR;
                    newWorld[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                    ter.renderFrame(newWorld);
                    hudDisplay(myMouse(), getTime(), newWorld);
                }
            }
            if (openKey == 's' || openKey == 'S') {
                Position avPosNew = new Position(avPos.x, avPos.y - 1);
                if (newWorld[avPosNew.x][avPosNew.y] == Tileset.WALL || newWorld[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    ter.renderFrame(newWorld);
                } else {
                    newWorld[avPos.x][avPos.y] = Tileset.FLOOR;
                    newWorld[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                    ter.renderFrame(newWorld);
                    hudDisplay(myMouse(), getTime(), newWorld);
                }
            }
            if (openKey == 'a' || openKey == 'A') {
                Position avPosNew = new Position(avPos.x - 1, avPos.y);
                if (newWorld[avPosNew.x][avPosNew.y] == Tileset.WALL || newWorld[avPosNew.x][avPosNew.y] == Tileset.LOCKED_DOOR) {
                    ter.renderFrame(newWorld);
                } else {
                    newWorld[avPos.x][avPos.y] = Tileset.FLOOR;
                    newWorld[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                    ter.renderFrame(newWorld);
                    hudDisplay(myMouse(), getTime(), newWorld);
                }
            }
            if (openKey == 'd' || openKey == 'D') {
                Position avPosNew = new Position(avPos.x + 1, avPos.y);
                if (newWorld[avPosNew.x][avPosNew.y] != Tileset.WALL && newWorld[avPosNew.x][avPosNew.y] != Tileset.LOCKED_DOOR) {
                    newWorld[avPos.x][avPos.y] = Tileset.FLOOR;
                    newWorld[avPosNew.x][avPosNew.y] = Tileset.AVATAR;
                    avPos.x = avPosNew.x;
                    avPos.y = avPosNew.y;
                    ter.renderFrame(newWorld);
                    hudDisplay(myMouse(), getTime(), newWorld);
                }
            }
            if (openKey == 'o' || openKey == 'O') {
                avPos.x = oldWorldAvatarPosition.x;
                avPos.y = oldWorldAvatarPosition.y;
                world[lockedDoorPos.x][lockedDoorPos.y] = Tileset.UNLOCKED_DOOR;
                ter.renderFrame(world);
                hudDisplay(myMouse(), getTime(), world);
                inMainWorld = true;
                break;
            }

        }
    }

    public void saveGame() {
        // seed on one line
        // gameString on the next
        File file = new File("./game.txt");
        try {
            if (!file.exists()) {
                file.createNewFile();
            }
            PrintWriter writer = new PrintWriter("game.txt", StandardCharsets.UTF_8);
            writer.print(seed);
            writer.print(" ");
            writer.print(randomAv.x);
            writer.print(" ");
            writer.print(randomAv.y);
            writer.print(" ");
            if (world[lockedDoorPos.x][lockedDoorPos.y] == Tileset.LOCKED_DOOR) {
                writer.print(1);
                writer.print(" ");
            } else {
                writer.print(0);
                writer.print(" ");
            }
            writer.print(lockedDoorPos.x);
            writer.print(" ");
            writer.print(lockedDoorPos.y);
            writer.close();
        } catch (IOException exception) {
            System.out.println(exception);
            System.exit(0);
        }
    }
}