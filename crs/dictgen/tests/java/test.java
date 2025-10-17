public String foo(int i, String inputString) {
	System.out.println("Received int = " + i + ", string = \"" + inputString + "\".");

	if (i == 42) {
		System.out.println("The integer is 42, which should be a token.");
	}

	if ("token".equals(inputString)) {
		System.out.println("The string matches \"token\". It should be a token.");
	}

	String[] substrings = inputString.split("\\s+");
	for (String substring : substrings) {
		if ("token2".equals(substring)) {
			System.out.println("Substring matches \"token\". It should be a token.");
		} else if ("magic".equals(substring)) {
			System.out.println("Substring matches \"magic\". It should be a token.");
		} else {
			System.out.println("Substring \"" + substring + "\" does not match any token.");
		}
	}

	switch (i) {
	case 0x42:
		System.out.println("Case 0x42 triggered.");
		break;
	case 0x43:
		System.out.println("Case 0x43 triggered.");
		break;
	default:
		System.out.println("The integer is not 0x42 or 0x43.");
	}
	return "not a token";
}
