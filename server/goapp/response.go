package main

import (
    "github.com/golang/protobuf/proto"
    "github.com/vegetable68/sbb-implementation/proto/sbb"
    "fmt"
    "os"
    "encoding/hex"
    "encoding/json"
    //b64 "encoding/base64"
    "strings"
    "io/ioutil"
    "net/http"
    "log"
    "github.com/cloudflare/circl/oprf"
)

type Config struct {
	CoarseEmbedLen	int	`json:"coarse_embed_len"`
	CoarseThreshold	int	`json:"coarse_threshold"`
	FileType	string	`json:"filetype"`
	FilePath	string	`json:"filepath"`
	ClientMatch	string	`json:"client_match"`
	Bucketized	bool	`json:"bucketized"`
	UseSecureSketch	bool	`json:"use_secure_sketch"`
	SimEmbedLen	int	`json:"embed_len"`
	M	int	`json:"Reed-Muller M"`
	R	int	`json:"Reed-Muller R"`
	K	int	`json:"Reed-Muller K"`
}


var server *oprf.Server

func toBytes(s string) []byte {
	bytes, _ := hex.DecodeString(s)
	return bytes
}

func toListBytes(s string) [][]byte {
	strs := strings.Split(s, "SEPARATOR")
	out := make([][]byte, len(strs))
	for i := range strs {
		fmt.Printf("++%s++", strs[i])
		out[i] = toBytes(strs[i])
	}
	return out
}

func readFile(fileName string) []byte {
	jsonFile, err := os.Open(fileName)
	if err != nil {
		fmt.Println("File %v can not be opened. Error: %v", fileName, err)
	}
	defer jsonFile.Close()
	input, _ := ioutil.ReadAll(jsonFile)

	return input
}


func toListString(input [][]byte) string{
	out := ""
	for j := range input {
		if out != "" {
			out = out + "," + hex.Dump(input[j])
		} else {
			out = out + hex.Dump(input[j])
		}
	}
	return out
}

func EvaluateServer(w http.ResponseWriter, req *http.Request) {
	myClient := sbb.SBBRequest{}

	data, err := ioutil.ReadAll(req.Body)
        if err != nil {
            fmt.Println(err)
        }

        if err := proto.Unmarshal(data, &myClient); err != nil {
            fmt.Println(err)
        }

	eval, err := server.Evaluate(myClient.Blinded)
	if err != nil {
		log.Fatal("invalid evaluation of server: " + err.Error())
	}

	result := sbb.SBBResponse{Evaluation: eval.Elements}
	response, err := proto.Marshal(&result)
	w.Write(response)
}



func main() {
    //load config
    fileInput := readFile("../../config.json")
    var config Config
    json.Unmarshal(fileInput, &config)

    suite := oprf.OPRFP256
    keyfile :=  fmt.Sprintf("%s/server_data_processed/%s/server-key", config.FilePath, config.FileType)
    pkS := readFile(keyfile)
    privateKey := new(oprf.PrivateKey)
    _ = privateKey.Deserialize(suite, pkS)
    server, _ = oprf.NewServer(suite, privateKey)

    http.HandleFunc("/evaluate", EvaluateServer)
    err := http.ListenAndServe("0.0.0.0:8888", nil)

    if err != nil {
        log.Fatal("ListenAndServe: ", err)
    }
}
