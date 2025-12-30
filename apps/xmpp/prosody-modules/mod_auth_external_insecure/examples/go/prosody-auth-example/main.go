package main

import "fmt"
import "bufio"
import "os"
import "strings"

const (
	ACTION = iota
	USER
	HOST
	PASSWORD
)

func main() {
	stdin := bufio.NewScanner(os.Stdin)
	for stdin.Scan() {
		parts := strings.SplitN(stdin.Text(), ":", 4)
		switch parts[ACTION] {
			case "auth":
				if parts[USER] == "someone" {
					fmt.Printf("1\n")
					continue
				}
				
			default: fmt.Printf("0\n")
		}
	}
}
