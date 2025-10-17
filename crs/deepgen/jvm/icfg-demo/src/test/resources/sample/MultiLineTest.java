public class MultiLineTest {
    public static void main(String[] args) {
        int result = calculateSum(
            1, 2, 3,
            4, 5
        );
        
        if (result > 10 &&
            result < 20) {
            System.out.println("Result is: " + result);
        }
    }
    
    public static int calculateSum(int a, int b, int c, int d, int e) {
        return a + b + c + d + e;
    }
}