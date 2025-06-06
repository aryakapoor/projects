package byow.Core;

import byow.TileEngine.TETile;

import java.util.ArrayList;
import java.util.Random;

import byow.TileEngine.Tileset;
import edu.princeton.cs.algs4.StdRandom;

public class Avatar {
    Position avPos;
    Integer xTile;
    Integer yTile;

    public Avatar(ArrayList<Integer> space){
        Integer x = StdRandom.uniform(0, space.size());
        Integer pos = space.get(x);
        avPos = Position.intToInt(pos);
    }

    public Position getAvPos(){
        return avPos;
    }
}
