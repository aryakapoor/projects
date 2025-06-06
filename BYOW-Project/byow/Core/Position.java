package byow.Core;

public class Position {
    int x;
    int y;
    Position(int x, int y) {
        this.x = x;
        this.y = y;
    }

    public Position shift(int dx, int dy) {
        return new Position(this.x + dx, this.y + dy);
    }

    public int positionToInt() {
        return Engine.WIDTH * this.y + this.x;
    }
    public static Position intToInt(Integer i) {
        Integer xPos = Engine.WIDTH % i;
        Integer yPos = Engine.HEIGHT / i; // assuming it rounds down
        return new Position(xPos, yPos);
    }

}