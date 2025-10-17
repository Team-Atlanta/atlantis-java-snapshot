char *foo(int i, char *long_variable_name_for_string) {
  printf("Received int = %d, string = \"%s\".\n", i,
         long_variable_name_for_string);

  if (i == 42) {
    printf("The integer is 42, which should be a token\n");
  }

  /*
   * some random strings in comments. these strings should not be tokens
   */
  if (strcmp(long_variable_name_for_string, "token") == 0) {
    printf("The string matches \"token\". it should be a token\n");
  }

  char *buf = malloc(1025);
  strncpy(buf, long_variable_name_for_string, 1024);
  if(strcmp(buf, "token2") == 0) {
	printf("\"token2\" matches to the copied string. it should be a token\n");
  }

  switch (i) {
  case 0x42:
	break;
  case 0x43:
	break;
  default:
	printf("The integer is not 0x42 or 0x43\n");
  }
  return "not a token";
}
