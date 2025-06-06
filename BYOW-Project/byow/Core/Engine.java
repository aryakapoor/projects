package byow.Core;

import byow.InputDemo.KeyboardInputSource;
import byow.InputDemo.StringInputDevice;

import byow.TileEngine.TETile;

public class Engine {
    public static final int WIDTH = 80;
    public static final int HEIGHT = 30;
    private TETile[][] WORLD = new TETile[WIDTH][HEIGHT];

    /**
     * Method used for exploring a fresh world. This method should handle all inputs,
     * including inputs from the main menu.
     */
    public void interactWithKeyboard() {
        Game game = new Game();
        game.startScreen();
        KeyboardInputSource kis = new KeyboardInputSource();
        WORLD = game.startScreen(kis);
    }

    /**
     * Method used for autograding and testing your code. The input string will be a series
     * of characters (for example, "n123sswwdasdassadwas", "n123sss:q", "lwww". The engine should
     * behave exactly as if the user typed these characters into the engine using
     * interactWithKeyboard.
     * <p>
     * Recall that strings ending in ":q" should cause the game to quite save. For example,
     * if we do interactWithInputString("n123sss:q"), we expect the game to run the first
     * 7 commands (n123sss) and then quit and save. If we then do
     * interactWithInputString("l"), we should be back in the exact same state.
     * <p>
     * In other words, running both of these:
     * - interactWithInputString("n123sss:q")
     * - interactWithInputString("lww")
     * <p>
     * should yield the exact same world state as:
     * - interactWithInputString("n123sssww")
     *
     * @param input the input string to feed to your program
     * @return the 2D TETile[][] representing the state of the world
     */
    public TETile[][] interactWithInputString(String input) {
        Game game = new Game();
        StringInputDevice str = new StringInputDevice(input);
        WORLD = game.startScreen(str);
        return WORLD;
    }
}
