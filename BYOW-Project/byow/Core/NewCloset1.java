package byow.Core;

import byow.TileEngine.TERenderer;
import byow.TileEngine.TETile;
import byow.TileEngine.Tileset;

import java.util.ArrayList;

public class NewCloset1 {
    /* Feel free to change the width and height. */
    public static final int WIDTH = 80;
    public static final int HEIGHT = 30;

    public TETile[][] worldTwo;

    public NewCloset1() {
        worldTwo = new TETile[WIDTH][HEIGHT];
    }

    public void fillBoardWithNothing(TETile[][] tiles) {
        int height = tiles[0].length;
        int width = tiles.length;
        for (int x = 0; x < width; x += 1) {
            for (int y = 0; y < height; y += 1) {
                tiles[x][y] = Tileset.NOTHING;
            }
        }
    }

    public void drawWorld(TETile[][] tiles) {
        fillBoardWithNothing(tiles);
        Position closetStartPosition = new Position(40, 25);
        drawRow(worldTwo, closetStartPosition, Tileset.WALL, 7); //draw top wall
        closetStartPosition = closetStartPosition.shift(0, -1);
        for (int i = 0; i < 9; i++) {
            drawRow(worldTwo, closetStartPosition, Tileset.WALL, 1);
            drawRow(worldTwo, closetStartPosition.shift(1, 0), Tileset.FLOOR, 5);
            drawRow(worldTwo, closetStartPosition.shift(6, 0), Tileset.WALL, 1);
            closetStartPosition = closetStartPosition.shift(0, -1);
        }
        drawRow(worldTwo, closetStartPosition, Tileset.WALL, 7); //draw bottom wall
        background(tiles);
    }

    public void drawRow(TETile[][] tiles, Position p, TETile tile, int length) {
        for (int dx = 0; dx < length; dx++) {
            if ((p.x+dx)==WIDTH){
                return;
            }
            tiles[p.x + dx][p.y] = tile;
        }
    }

    public void background(TETile[][] tiles) {
        int height = tiles[0].length;
        int width = tiles.length;
        for (int x = 0; x < width; x += 1) {
            for (int y = 0; y < height; y += 1) {
                if (tiles[x][y] == Tileset.NOTHING) {
                    tiles[x][y] = Tileset.GRASS;
                }
            }
        }
    }


    public TETile[][] returnClosetWorld() {
        drawWorld(worldTwo);
        return worldTwo;
    }

    public ArrayList<Position> floorArray() {
        ArrayList<Position> floorPos = new ArrayList<>();
        for (int i = 0; i < WIDTH; i++) {
            for (int j = 0; j < HEIGHT; j++) {
                if (worldTwo[i][j] == Tileset.FLOOR) {
                    floorPos.add(new Position(i, j));
                }
            }
        }
        return floorPos;
    }

    public TETile[][] goBackToOldWorld(TETile[][] world) {
        TERenderer ter = new TERenderer();
        ter.initialize(WIDTH, HEIGHT);
        drawWorld(world);
        ter.renderFrame(world);
        return world;
    }
}
