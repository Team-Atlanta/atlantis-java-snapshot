public class SampleClass {
    
    public static void main(String[] args) {
        SampleClass sample = new SampleClass();
        sample.methodA();
        sample.methodB(5);
    }
    
    public void methodA() {
        System.out.println("Method A called");
        methodC();
    }
    
    public int methodB(int x) {
        if (x > 0) {
            return methodD(x - 1);
        } else {
            return 0;
        }
    }
    
    private void methodC() {
        System.out.println("Method C called");
    }
    
    private int methodD(int y) {
        return y * 2;
    }
}