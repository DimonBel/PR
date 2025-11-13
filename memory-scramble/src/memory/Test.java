package memory;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.io.File;

public class Test {

    public static void main(String[] args) {
        Path filePath = Paths.get("boards/vova.txt"); // Replace with your file path
        String oldText = "ff";
        String newText = "replacement text";

        try {
            String fileContent = Files.readString(filePath);
            String modifiedContent = fileContent.replace(oldText, newText);
            Files.writeString(filePath, modifiedContent);
            System.out.println("Text replaced successfully!");
        } catch (IOException e) {
            System.err.println("Error replacing text in file: " + e.getMessage());
        }



        File myObj = new File("boards/filename.txt"); // Create File object

        if (myObj.exists()) {
            try {
                if (myObj.createNewFile()) {           // Try to create the file
                    System.out.println("File created: " + myObj.getName());
                } else {
                    System.out.println("File already exists.");
                }
            } catch (IOException e) {
                System.out.println("An error occurred.");
                e.printStackTrace(); // Print error details
            }
        }

        else {
            System.out.println("Good luck");
        }


    }
}
