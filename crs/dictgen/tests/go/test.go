func foo(i int, inputString string) string {
	fmt.Printf("Received int = %d, string = \"%s\".\n", i, inputString)

	if i == 42 {
		fmt.Println("The integer is 42, which should be a token.")
	}

	j := i
	if j == 43 {
		fmt.Println("The integer is 43, which should be a token.")
	}

	if inputString == "token" {
		fmt.Println("The string matches \"token\". It should be a token.")
	}

	subString1 := inputString[2:5]
	if subString1 == "token2" {
		fmt.Println("The substring matches \"token2\". It should be a token.")
	}

	if inputString[0] == 't' {
		fmt.Println("The first character of the string is 't'. It should be a token.")
	} else if inputString[6:10] == "token3" {
		fmt.Println("The substring matches \"token3\". It should be a token.")
	} else {
		fmt.Println("no token")
	}

	switch i {
	case 0x42:
		fmt.Println("Case 0x42 triggered.")
	case 0x43:
		fmt.Println("Case 0x43 triggered.")
	default:
		fmt.Println("The integer is not 0x42 or 0x43.")
	}
	return "not a token"
}
