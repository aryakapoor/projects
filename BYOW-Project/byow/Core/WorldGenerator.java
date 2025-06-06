package byow.Core;

import byow.TileEngine.TERenderer;
import byow.TileEngine.TETile;
import byow.TileEngine.Tileset;

import java.util.*;

public class WorldGenerator {
    /* Feel free to change the width and height. */
    public static final int WIDTH = 80;
    public static final int HEIGHT = 30;
    public TETile[][] world = new TETile[WIDTH][HEIGHT];
    public ArrayList<Integer> allOccupiedSpace = new ArrayList<>();
    private ArrayList<Room> roomList = new ArrayList<>();
    private ArrayList<Room> roomGraphList = new ArrayList<>();
    public HashMap<Room, Room> roomGraph = new HashMap<>(); // maps a room to its closest room

    public ArrayList<Coin> coinList = new ArrayList<>();
    public Random myRand = new Random(Long.parseLong(Game.seed));

    public static void fillBoardWithNothing(TETile[][] tiles) {
        for (int x = 0; x < WIDTH; x += 1) {
            for (int y = 0; y < HEIGHT; y += 1) {
                tiles[x][y] = Tileset.NOTHING;
            }
        }
    }

    public void addOneRoom() {
        Position randomPosition = new Position(myRand.nextInt(0, 70), myRand.nextInt(12, 30));
        Room testRoom = new Room(randomPosition);
        roomList.add(testRoom);
    }

    public void drawRow(TETile[][] tiles, Position p, TETile tile, int length) {
        for (int dx = 0; dx < length; dx++) {
            if ((p.x + dx) == WIDTH) {
                return;
            }
            tiles[p.x + dx][p.y] = tile;
        }
    }

    public void drawCol(TETile[][] tiles, Position p, TETile tile, int length) {
        for (int dy = 0; dy < length; dy++) {
            if ((p.y + dy) == HEIGHT) {
                return;
            }
            tiles[p.x][p.y + dy] = tile;
        }
    }

    public void generateRooms() {
        int numberOfRooms = myRand.nextInt(19, 20);
        for (int i = 0; i < numberOfRooms; i++) {
            Position randomPosition = new Position(myRand.nextInt(0, 70), myRand.nextInt(12, 30));
            Room testRoom = new Room(randomPosition);
            if (!testRoom.overlaps()) {
                testRoom.generateRoom();
                roomList.add(testRoom);
            }
        }
    }

    public Integer distance(Position centerOne, Position centerTwo) {
        Integer a = Math.abs(centerOne.x - centerTwo.x);
        Integer b = Math.abs(centerOne.y - centerTwo.y);
        return (int) Math.round(Math.sqrt(a * a + b * b));
    }

    public void drawWorld(TETile[][] tiles) {
        fillBoardWithNothing(tiles);
        generateRooms();
        clearColors();
        buildGraph();
        connectAllRooms();
        clearColors();
        patchWalls();
        background(tiles);
        clearColors();
        //drawCoins();


        /*
        Position testPositon1 = new Position(10, 20);
        Room testRoom1 = new Room(testPositon1);
        Position testPositon2 = new Position(30, 10);
        Room testRoom2 = new Room(testPositon2);
        testRoom1.generateRoom();
        testRoom2.generateRoom();
        tiles[testRoom1.center().x][testRoom1.center().y] = Tileset.LOCKED_DOOR;
        tiles[testRoom2.center().x][testRoom2.center().y] = Tileset.LOCKED_DOOR;
        connectTwoRooms(testRoom1, testRoom2);
        //patchWalls();
        //clearColors();

         */


        /*
        Position testPosition1 = new Position(20, 20);
        Room testRoom1 = new Room(testPosition1);
        testRoom1.generateRoom();
        System.out.println(testRoom1.center());
        Position testPosition2 = new Position(40, 20);
        Room testRoom2 = new Room(testPosition2);
        testRoom2.generateRoom();
        tiles[testRoom1.center().x][testRoom1.center().y] = Tileset.FLOWER;
        tiles[testRoom2.center().x][testRoom2.center().y] = Tileset.FLOWER;
        tiles[testRoom1.startPosition.x][testRoom1.startPosition.y] = Tileset.LOCKED_DOOR;
        System.out.println(testRoom1.height);
        System.out.println(testRoom1.width);

         */

        //connectTwoRooms(testRoom1, testRoom2);
    }

    public void drawCoins() {
        int numCoins = myRand.nextInt(5,10);
        for (int i = 0; i < numCoins; i++) {
            Coin newCoin = new Coin();
            if (world[newCoin.coinPos.x][newCoin.coinPos.y]!=Tileset.AVATAR || world[newCoin.coinPos.x][newCoin.coinPos.y]!=Tileset.WALL){
                    world[newCoin.coinPos.x][newCoin.coinPos.y] = Tileset.FLOWER;
                    coinList.add(newCoin);
                }
            }
    }

    public void clearColors() {
        for (int i = 1; i < HEIGHT - 3; i++) {
            for (int j = 1; j < WIDTH - 3; j++) {
                if ((world[j][i + 1] == Tileset.FLOOR && world[j][i - 1] == Tileset.FLOOR)
                        || (world[j + 1][i] == Tileset.FLOOR && world[j - 1][i] == Tileset.FLOOR)) {
                    world[j][i] = Tileset.FLOOR;
                }
            }
        }
    }

    public void patchWalls() {
        for (int i = 1; i < HEIGHT - 3; i++) {
            for (int j = 1; j < WIDTH - 3; j++) {
                if (world[j][i] == Tileset.FLOOR && world[j + 1][i] == Tileset.NOTHING) {
                    world[j + 1][i] = Tileset.WALL;
                }
                if (world[j][i] == Tileset.FLOOR && world[j][i + 1] == Tileset.NOTHING) {
                    world[j][i + 1] = Tileset.WALL;
                }
                if (world[j][i] == Tileset.FLOOR && world[j - 1][i] == Tileset.NOTHING) {
                    world[j - 1][i] = Tileset.WALL;
                }
                if (world[j][i] == Tileset.FLOOR && world[j][i - 1] == Tileset.NOTHING) {
                    world[j][i - 1] = Tileset.WALL;
                }
            }
        }
    }

    public void buildGraph() {
        // maps a room to another room it shares a hallway with
        int randomIndex = myRand.nextInt(roomList.size());
        Room randomStartingRoom = roomList.get(randomIndex);
        roomList.remove(randomStartingRoom);
        while (roomList.size() > 0) {
            Room closestRoom = findClosestRoom(randomStartingRoom);
            roomGraph.put(randomStartingRoom, closestRoom);
            roomGraphList.add(randomStartingRoom);
            roomList.remove(closestRoom);
            randomStartingRoom = closestRoom;
        }
    }

    public Room findClosestRoom(Room r) {
        HashMap<Integer, Room> distanceToRoom = new HashMap<>();
        for (Room room : roomList) {
            Integer dist = distance(r.center(), r.center());
            distanceToRoom.put(dist, room);
        }

        Integer shortestDistance = 99;
        for (Integer i : distanceToRoom.keySet()) {
            if (i < shortestDistance) {
                shortestDistance = i;
            }
        }
        return distanceToRoom.get(shortestDistance);
    }

    public void connectTwoRooms(Room start, Room destination) {
        /*
        Position startCenter = start.center();
        Position destinationCenter = destination.center();
        drawCol(world, startCenter, Tileset.WALL, startCenter.y - destinationCenter.y);
        drawRow(world, startCenter, Tileset.WALL, startCenter.x - destinationCenter.x);

         */
        if (start.center().x == destination.center().x && start.center().y < destination.center().y) {
            Hallway testHallway = new Hallway();
            testHallway.generateVerticalHallway(start.center(), destination.center().y - start.center().y);
        }
        if (start.center().x == destination.center().x && start.center().y > destination.center().y) {
            Hallway testHallway = new Hallway();
            testHallway.generateVerticalHallway(start.center(), start.center().y - destination.center().y);
        }
        if (start.center().y == destination.center().y && start.center().x < destination.center().x) {
            Hallway testHallway = new Hallway();
            testHallway.generateHorizontalHallway(start.center(), destination.center().x - start.center().x);
        }
        if (start.center().y == destination.center().y && start.center().x > destination.center().x) {
            Hallway testHallway = new Hallway();
            testHallway.generateHorizontalHallway(destination.center(), start.center().x - destination.center().x);
        }
        if (start.center().y < destination.center().y && start.center().x < destination.center().x) {
            Hallway testHallway = new Hallway();
            Hallway testHallwayTwo = new Hallway();
            testHallwayTwo.generateHorizontalHallway(start.center().shift(0, destination.center().y - start.center().y),
                    destination.center().x - start.center().x);
            testHallway.generateVerticalHallway(start.center(), destination.center().y - start.center().y);
        }
        if (start.center().y < destination.center().y && start.center().x > destination.center().x) {
            Hallway testHallway = new Hallway();
            Hallway testHallwayTwo = new Hallway();
            testHallwayTwo.generateHorizontalHallway(destination.center(), start.center().x - destination.center().x + 2);
            testHallway.generateVerticalHallway(start.center(), destination.center().y - start.center().y);
        }
        if (start.center().y > destination.center().y && start.center().x > destination.center().x) {
            Hallway testHallway = new Hallway();
            Hallway testHallwayTwo = new Hallway();
            testHallwayTwo.generateHorizontalHallway(destination.center().shift(0, start.center().y - destination.center().y)
                    , start.center().x - destination.center().x);
            testHallway.generateVerticalHallway(destination.center(), start.center().y - destination.center().y);
        }
        if (start.center().y > destination.center().y && start.center().x < destination.center().x) {
            Hallway testHallway = new Hallway();
            Hallway testHallwayTwo = new Hallway();
            testHallwayTwo.generateHorizontalHallway(destination.center().shift((destination.center().x - start.center().x) * -1
                    , 0), destination.center().x - start.center().x);
            testHallway.generateVerticalHallway(start.center().shift(0, (start.center().y - destination.center().y) * -1),
                    start.center().y - destination.center().y);
        }
    }

    public void background(TETile[][] tiles) {
        for (int x = 0; x < WIDTH; x += 1) {
            for (int y = 0; y < HEIGHT; y += 1) {
                if (tiles[x][y] == Tileset.NOTHING) {
                    tiles[x][y] = Tileset.WATER;
                }
            }
        }
    }

    public void connectAllRooms() {
        for (Room r : roomGraphList) {
            connectTwoRooms(r, roomGraph.get(r));
        }
    }

    public TETile[][] returnWorld() {
        TERenderer ter = new TERenderer();
        ter.initialize(WIDTH, HEIGHT);
        drawWorld(world);
        ter.renderFrame(world);
        return world;

    }

    public ArrayList<Position> chooseRandomFloor() {
        ArrayList<Position> floorPos = new ArrayList<>();
        for (int i = 0; i < WIDTH; i++) {
            for (int j = 0; j < HEIGHT; j++) {
                if (world[i][j] == Tileset.FLOOR) {
                    floorPos.add(new Position(i, j));
                }
            }
        }
        return floorPos;
    }

    public void main(String[] args) {
        TERenderer ter = new TERenderer();
        ter.initialize(WIDTH, HEIGHT);
        // make call to interact with string
        drawWorld(world);
        ter.renderFrame(world);
    }

    public class Room {
        public int width;
        public int height;
        public Position startPosition;
        public ArrayList<Position> walls;

        public TETile[][] roomWorld;

        public Room(Position startingPosition) {
            //constructor of a room (not necessarily placed down yet
            width = 5 + myRand.nextInt(5);
            height = 5 + myRand.nextInt(5);
            startPosition = startingPosition;

            //adding to the list in walls
            walls = new ArrayList<>();
            Position upperPosition = startPosition;
            //adding the top wall
            for (int i = 0; i < width; i++) {
                walls.add(upperPosition);
                upperPosition = upperPosition.shift(1, 0);
            }
            //adding bottom wall
            Position lowerPosition = startPosition.shift(0, (height - 1) * -1);
            for (int i = 0; i < width; i++) {
                walls.add(lowerPosition);
                lowerPosition = lowerPosition.shift(1, 0);
            }
            //left wall
            Position leftPosition = startPosition.shift(0, -1);
            for (int i = 1; i < height; i++) {
                walls.add(leftPosition);
                leftPosition = leftPosition.shift(0, -1);
            }
            //right wall
            Position rightPosition = startPosition.shift(width - 1, 0);
            for (int i = 1; i < height; i++) {
                walls.add(rightPosition);
                rightPosition = rightPosition.shift(0, -1);
            }
            roomWorld = world;
        }

        public void generateRoom() {
            //check to see if they are occupied
            for (Integer i : this.getSpan()) {
                allOccupiedSpace.add(i);
            }

            //draws out the rooms on 2D board
            drawRow(roomWorld, startPosition, Tileset.WALL, width); //draw top wall
            startPosition = startPosition.shift(0, -1);
            for (int i = 0; i < height - 2; i++) {
                drawRow(roomWorld, startPosition, Tileset.WALL, 1);
                drawRow(roomWorld, startPosition.shift(1, 0), Tileset.FLOOR, width - 2);
                drawRow(roomWorld, startPosition.shift(width - 1, 0), Tileset.WALL, 1);
                startPosition = startPosition.shift(0, -1);
            }
            drawRow(roomWorld, startPosition, Tileset.WALL, width); //draw bottom wall

        }

        //returns the Position of all the walls in a room
        public ArrayList<Position> getWalls() {
            return walls;
        }

        public ArrayList<Integer> getSpan() {
            ArrayList<Integer> span = new ArrayList<>();
            Position occupyPosition = startPosition;
            for (int g = 0; g < height + 4; g++) {
                //running through the columns
                for (int i = 0; i < width + 4; i++) {
                    span.add(occupyPosition.positionToInt());
                    occupyPosition = occupyPosition.shift(1, 0);
                }
                occupyPosition = occupyPosition.shift(width * -1, -1);
            }
            return span;
        }

        public Boolean overlaps() {
            Boolean overlap = false;
            for (Integer position : this.getSpan()) {
                if (allOccupiedSpace.contains(position)) {
                    overlap = true;
                }
            }
            return overlap;
        }

        public Position center() {
            Position center = new Position(startPosition.x + (this.width / 2), startPosition.y + (this.height / 2));
            return center;
        }
    }

    public class Hallway {

        public int width;
        public int length;
        public Position start;

        public TETile[][] hallwayWorld;


        public Hallway() {
            //width = MapGenerator.myRand.nextInt(1, 3);
            width = 2;
            hallwayWorld = world;
        }

        public void generateHorizontalHallway(Position position, int len) {
            length = len;
            //drawing the top wall
            Position drawPosition = position;
            start = position;
            drawRow(hallwayWorld, drawPosition, Tileset.WALL, this.length);
            drawPosition = drawPosition.shift(0, -1);
            //drawing the floor
            for (int i = 0; i < this.width; i++) {
                drawRow(hallwayWorld, drawPosition, Tileset.FLOOR, this.length);
                drawPosition = drawPosition.shift(0, -1);
            }
            //drawing the bottom wall
            drawRow(hallwayWorld, drawPosition, Tileset.WALL, this.length);
        }

        public void generateVerticalHallway(Position position, int len) {
            //drawing the left wall
            length = len;
            Position drawPosition = position;
            start = position;
            drawCol(hallwayWorld, drawPosition, Tileset.WALL, this.length);
            drawPosition = drawPosition.shift(1, 0);
            //drawing the floors
            for (int i = 0; i < this.width; i++) {
                drawCol(hallwayWorld, drawPosition, Tileset.FLOOR, this.length);
                drawPosition = drawPosition.shift(1, 0);
            }
            //drawing th bottom col
            drawCol(hallwayWorld, drawPosition, Tileset.WALL, this.length - 1);

        }
    }
    public class Coin {
        public Position coinPos;
        public Coin() {
            ArrayList<Position> floorTile = chooseRandomFloor();
            int randomIndex = myRand.nextInt(floorTile.size());
            coinPos = floorTile.get(randomIndex);
        }
    }
}


