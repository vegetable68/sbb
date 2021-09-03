package main

import (
	"strings"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
	"github.com/cloudflare/circl/oprf"
	"os"
	"io/ioutil"
)



func toBytes(s string) []byte {
	bytes, _ := hex.DecodeString(s)
	return bytes
}

func toListBytes(s string) [][]byte {
	strs := strings.Split(s, ",")
	out := make([][]byte, len(strs))
	for i := range strs {
		out[i] = toBytes(strs[i])
	}
	return out
}

func ServerKeyGen() []byte{
	suite := oprf.OPRFP256
	privateKey, _ := oprf.GenerateKey(suite)
	pks, _ := privateKey.Serialize()
	return pks
}

func ServerEncrypt(pkS []byte, inputStr string, infoStr string) (string){
	var server *oprf.Server
	suite := oprf.OPRFP256
	privateKey := new(oprf.PrivateKey)
	//pkS := toBytes(encodedKey)
	_ = privateKey.Deserialize(suite, pkS)
	server, _ = oprf.NewServer(suite, privateKey)

	info := toBytes(infoStr)
	input := toBytes(inputStr)
	output, _ := server.FullEvaluate(input, info)
	out := hex.Dump(output)
	return out
}


func readFile(fileName string) []string {
	jsonFile, err := os.Open(fileName)
	if err != nil {
		fmt.Println("File %v can not be opened. Error: %v", fileName, err)
	}
	defer jsonFile.Close()
	input, _ := ioutil.ReadAll(jsonFile)

	var v []string
	err = json.Unmarshal(input, &v)
	if err != nil {
		fmt.Println("File %v can not be loaded. Error: %v", fileName, err)
	}
	return v
}

func main() {
    filepath := "/data/yiqing/expr_data"
    filelst :=  [5]string{"blocklst_2pow13", "blocklst_2pow14", "blocklst_2pow15", "blocklst_2pow16", "blocklst_2pow17"}

    for i := 0; i < len(filelst); i++ {
      file := filelst[i]
      fmt.Println(file)
      start := time.Now()
      filename := fmt.Sprintf("%s/server_data_processed/%s/random_generator.json", filepath, file)
      hashes := readFile(filename)
      key := ServerKeyGen()
      info := "736f6d655f696e666f"
      out := make([]string, len(hashes))
      for i := range hashes {
          out[i] = ServerEncrypt(key, hashes[i], info)
      }
      filename = fmt.Sprintf("%s/server_data_processed/%s/server-key", filepath, file)
      ioutil.WriteFile(filename, key, 0644)
      jsonOut, _ := json.Marshal(out)
      filename = fmt.Sprintf("%s/server_data_processed/%s/encrypted_hashes.json", filepath, file)
      ioutil.WriteFile(filename, jsonOut, os.ModePerm)
      t := time.Now()
      elapsed := t.Sub(start)
      fmt.Println(elapsed)
    }

}
