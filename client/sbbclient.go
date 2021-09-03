package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/cloudflare/circl/oprf"
	"github.com/golang/protobuf/proto"
	"github.com/steakknife/hamming"
	"github.com/vegetable68/sbb-implementation/proto/sbb"
)

type Config struct {
	CoarseEmbedLen  int    `json:"coarse_embed_len"`
	CoarseThreshold int    `json:"coarse_threshold"`
	Threshold       int    `json:"threshold"`
	FileType        string `json:"filetype"`
	FilePath        string `json:"filepath"`
	ClientMatch     string `json:"client_match"`
	Bucketized      bool   `json:"bucketized"`
	UseSecureSketch bool   `json:"use_secure_sketch"`
	UseCrypten      bool   `json:"use_crypten"`
	UseEmp          bool   `json:"use_emp"`
	SimEmbedLen     int    `json:"embed_len"`
	M               int    `json:"Reed-Muller M"`
	R               int    `json:"Reed-Muller R"`
	K               int    `json:"Reed-Muller K"`
}

type SecureSketchHelper struct {
	MtxGen   string         `json:"gen_t"`
	MtxB     []string       `json:"mtx_b"`
	MtxBAux  []string       `json:"mtx_b_aux"`
	Masks    [][]int        `json:"masks"`
	Bitcount map[string]int `json:"bitcount"`
}

type ResponseTypeI struct {
	Hashes    string `json:"hashes"`
	Encrypted string `json:"encrypted"`
}

type ResponseTypeII struct {
	Hashes string `json:"hashes"`
}

type ResponseMPC struct {
	BucketSize int `json:"bucket_size"`
}

type EvaluationResponse struct {
	Evaluation string `json:"evaluation"`
}

type Result struct {
	FirstQueryTime  float64 `json:"first_query_time"`
	SecondQueryTime float64 `json:"second_query_time"`
	ClientFinalize  float64 `json:"client_finalize"`
	ClientTotal     float64 `json:"client_total_time"`
	SSClientTime    float64 `json:"ss_client_time"`
}

func toBytes(s string) []byte {
	bytes, _ := hex.DecodeString(s)
	return bytes
}

func toListInts(s string) [][]int {
	sep := "."
	strs := strings.Split(s, sep)
	out := make([][]int, len(strs))
	for i := range strs {
		sep = ","
		chars := strings.Split(strs[i], sep)
		out[i] = make([]int, len(chars))

		for j := range chars {
			out[i][j], _ = strconv.Atoi(chars[j])
		}
	}
	return out
}

func toListBytes(s string) [][]byte {
	sep := ","
	strs := strings.Split(s, sep)
	out := make([][]byte, len(strs))
	for i := range strs {
		out[i] = toBytes(strs[i])
	}
	return out
}

func input2ListBytes(s string) [][]byte {
	sep := "SEPARATOR"
	strs := strings.Split(s, sep)
	out := make([][]byte, len(strs))
	for i := range strs {
		out[i] = toBytes(strs[i])
	}
	return out
}

func compareLists(got string, want [][]byte) []int {
	var equals []int
	sep := "SEPARATOR"
	strs := strings.Split(got, sep)

	for i := range strs {
		if strs[i] == hex.Dump(want[i]) {
			equals = append(equals, i)
		}
	}
	return equals
}

func toListString(input [][]byte) string {
	out := ""
	sep := "SEPARATOR"
	for j := range input {
		if out != "" {
			out = out + sep + hex.Dump(input[j])
		} else {
			out = out + hex.Dump(input[j])
		}
	}
	return out
}

func clientFinalize(client *oprf.Client, cr *oprf.ClientRequest, eval [][]byte, infoStr string) [][]byte {
	info := toBytes(infoStr)

	var proof *oprf.Proof
	e := &oprf.Evaluation{eval, proof}

	ret, _ := client.Finalize(cr, e, info)
	return ret
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

func writeStringToNewFile(fileName string, str string) {
	f, err := os.Create(fileName)
	if err != nil {
		fmt.Println("File %v can not be opened. Error: %v", fileName, err)
	}
	defer f.Close()
	_, err = f.WriteString(str)
	if err != nil {
		fmt.Println("File %v could not be written to. Error: %v", fileName, err)
	}
}

func int2bytes(input []int) []byte {
	var cur byte
	var ret []byte
	var idx byte
	idx = 1
	for i := range input {
		if (i%8 == 0) && (i != 0) {
			ret = append(ret, cur)
			cur = 0
			idx = 1
		}
		cur = cur + idx*byte(input[i])
		idx = (idx << 1)
	}
	ret = append(ret, cur)
	return ret
}

func int2str(input []int) string {
	var ret string
	for i := range input {
		ret = ret + strconv.FormatInt(int64(input[i]), 10)
	}
	return ret
}

func main() {
	rand.Seed(time.Now().UTC().UnixNano())
	//load config
	fileInput := readFile("../config.json")
	var config Config
	var result Result
	json.Unmarshal(fileInput, &config)
	//fmt.Println(config)
	serverAddr := "172.31.29.104" //"172.31.11.68"

	//test input
	//load testdataset
	stringFilename := fmt.Sprintf("%s/client_data_processed/%s/client_%s_data_as_strings.json", config.FilePath, config.FileType, config.ClientMatch)
	var strings []string
	fileInput = readFile(stringFilename)
	json.Unmarshal(fileInput, &strings)
	bytesFilename := fmt.Sprintf("%s/client_data_processed/%s/client_%s_data_as_bytes.json", config.FilePath, config.FileType, config.ClientMatch)
	var byteslices []string
	fileInput = readFile(bytesFilename)
	json.Unmarshal(fileInput, &byteslices)
	chosenIdx := rand.Intn(len(strings))
	//fmt.Println(chosenIdx)

	//load secure sketch recovery helpers
	filename := fmt.Sprintf("%s/client_data_processed/client_side_secure_sketch_%d_%d.json", config.FilePath, config.M, config.R)
	fileInput = readFile(filename)
	var helper SecureSketchHelper
	_ = json.Unmarshal(fileInput, &helper)
	mtxB := make([][][]byte, len(helper.MtxB))
	for i := range helper.MtxB {
		mtxB[i] = toListBytes(helper.MtxB[i])
	}
	mtxBAux := make([][][]int, len(helper.MtxBAux))
	for i := range helper.MtxBAux {
		mtxBAux[i] = toListInts(helper.MtxBAux[i])
	}

	mtxGen := toListBytes(helper.MtxGen)
	var bitcount [256]int
	for i := 0; i < 256; i++ {
		bitcount[i] = helper.Bitcount[strconv.FormatInt(int64(i), 10)]
	}

	totalStart := time.Now()

	image := toBytes(byteslices[chosenIdx])

	if config.UseCrypten && config.UseEmp {
		panic("Config error: Crypten and EMP may not be used at the same time")
	}

	fmt.Println("chosen hash:", byteslices[chosenIdx])
	if config.UseCrypten || config.UseEmp {
		// Write byteslices[chosenIdx] to local file
		writeStringToNewFile("/tmp/client_hash", byteslices[chosenIdx]+"\n")
	}

	permedIdx := rand.Perm(config.SimEmbedLen)
	cols := ""
	vals := ""
	flipbias := 0.05
	for i := 0; i < config.CoarseEmbedLen; i++ {
		cols = cols + fmt.Sprintf("%03d", permedIdx[i])
		tmpFlip := rand.Float64()
		if tmpFlip <= flipbias {
			if strings[chosenIdx][permedIdx[i]] == '1' {
				vals = vals + "0"
			} else {
				vals = vals + "1"
			}
		} else {
			vals = vals + string(strings[chosenIdx][permedIdx[i]])
		}
	}

	if config.UseSecureSketch {

		//Transaction 1: query for the bucket
		start := time.Now()
		url := fmt.Sprintf("http://%s:8080/query?cols=%s&values=%s&bucketized=%v&use_secure_sketch=%v", serverAddr, cols, vals, config.Bucketized, config.UseSecureSketch)
		resp, err := http.Get(url)
		if err != nil {
			log.Fatal(err)
		}
		ansValue, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			panic(err.Error())
		}
		defer resp.Body.Close()

		t := time.Now()
		elapsed := t.Sub(start)
		//fmt.Println("First Query time:", elapsed)
		result.FirstQueryTime = float64(elapsed) / float64(time.Millisecond)
		//fmt.Println("First Query Response size", len(ansValue))

		var ans ResponseTypeI
		json.Unmarshal(ansValue, &ans)
		start = time.Now()

		// secure sketch recovery
		hashbytes := input2ListBytes(ans.Hashes)
		mtx_b_len := len(mtxB)
		clientInputs := ""
		majority := make([]int, config.R+1)
		for t := config.R; t >= 0; t-- {
			majority[t] = int(math.Pow(2, float64(config.M-t-1)))
		}

		for i := range hashbytes {
			embed_len := len(hashbytes[i])
			input := make([]byte, embed_len)
			for j := range hashbytes[i] {
				input[j] = hashbytes[i][j] ^ image[j]
			}
			f := input
			p := make([]int, mtx_b_len)
			for t := config.R; t >= 0; t-- {
				for j := range helper.Masks[t] {
					k := helper.Masks[t][j]
					tmpMtx := 0
					for tmpj := range mtxBAux[k] {
						tmp := 0
						for jj := range mtxBAux[k][tmpj] {
							tmpIdx := mtxBAux[k][tmpj][jj]
							tmp = tmp + (bitcount[mtxB[k][tmpj][tmpIdx]&f[tmpIdx]])
						}
						tmp = tmp % 2
						tmpMtx = tmpMtx + tmp
					}
					if tmpMtx <= majority[t] {
						tmpMtx = 0
					} else {
						tmpMtx = 1
					}
					p[k] = (p[k] + tmpMtx) % 2
				}
				p_bytes := int2bytes(p)
				tmpf := make([]int, len(mtxGen))
				for j := range mtxGen {
					tmp := 0
					for jj := range mtxGen[j] {
						tmp = tmp + bitcount[mtxGen[j][jj]&p_bytes[jj]]
					}
					tmpf[j] = (tmpf[j] + tmp) % 2
				}
				f = int2bytes(tmpf)
				for j := range input {
					f[j] = f[j] ^ input[j]
				}
			}
			if len(clientInputs) > 0 {
				clientInputs = clientInputs + "," + int2str(p)
			} else {
				clientInputs = clientInputs + int2str(p)
			}
		}

		t = time.Now()
		elapsed = t.Sub(start)
		//fmt.Println("SS Recovery Time:", elapsed)
		result.SSClientTime = float64(elapsed) / float64(time.Millisecond)
		start = time.Now()

		// client side oprf: request
		var client *oprf.Client
		suite := oprf.OPRFP256
		client, _ = oprf.NewClient(suite)

		cr, _ := client.Request(toListBytes(clientInputs))
		reqp := sbb.SBBRequest{Blinded: cr.BlindedElements}

		data, err := proto.Marshal(&reqp)
		if err != nil {
			//fmt.Println(err)
			return
		}

		//fmt.Println("Secure Sketch client size:", len(data))
		url = fmt.Sprintf("http://%s:8888/evaluate", serverAddr)
		resp, err = http.Post(url, "", bytes.NewBuffer(data))
		if err != nil {
			//fmt.Println(err)
			return
		}

		defer resp.Body.Close()
		buffer, err := ioutil.ReadAll(resp.Body)
		retEvals := sbb.SBBResponse{}
		err = proto.Unmarshal(buffer, &retEvals)

		t = time.Now()
		elapsed = t.Sub(start)
		//fmt.Println("Second Query Time:", elapsed)
		result.SecondQueryTime = float64(elapsed) / float64(time.Millisecond)
		start = time.Now()

		start = time.Now()

		// client side oprf: finalize
		infoStr := "736f6d655f696e666f"
		retAns := clientFinalize(client, cr, retEvals.Evaluation, infoStr)
		_ = compareLists(ans.Encrypted, retAns)

		// if there is overlap
		//fmt.Println("Answer:", equals)
		t = time.Now()
		elapsed = t.Sub(start)
		//fmt.Println("Client Side Finalize:", elapsed)
		result.ClientFinalize = float64(elapsed) / float64(time.Millisecond)

	} else {
		//Transaction 1: query for the bucket
		start := time.Now()
		url := fmt.Sprintf("http://%s:8080/query?cols=%s&values=%s&bucketized"+
			"=%v&use_secure_sketch=%v&use_crypten=%v&use_emp=%v",
			serverAddr, cols, vals, config.Bucketized, config.UseSecureSketch,
			config.UseCrypten, config.UseEmp)
		resp, err := http.Get(url)
		if err != nil {
			log.Fatal(err)
		}
		ansValue, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			panic(err.Error())
		}
		defer resp.Body.Close()

		t := time.Now()
		elapsed := t.Sub(start)
		//fmt.Println("First Query time:", elapsed)
		result.FirstQueryTime = float64(elapsed) / float64(time.Millisecond)

		if config.UseCrypten {
			fmt.Println("Using crypten")
			// start = time.Now()
			var ans ResponseMPC
			json.Unmarshal(ansValue, &ans)
			fmt.Println("The bucket size is", ans.BucketSize)
			fullCmd := fmt.Sprintf("export WORLD_SIZE=2; export RENDEZVOUS=env://"+
				"; export MASTER_ADDR=172.31.26.205; export MASTER_PORT=29500; "+
				" export RANK=0; source ~/miniconda3/etc/profile.d/conda.sh;"+
				" (conda activate crypten_env; python ../mpc_local/launcher.py"+
				" --bar=%v --size=%v; conda deactivate)",
				config.Threshold, ans.BucketSize) // took out background part
			fmt.Println("fullCmd", fullCmd)

			cryptenCmd := exec.Command("bash", "-c", fullCmd)
			output, err := cryptenCmd.Output()
			if err != nil {
				panic(err)
			}
			// t = time.Now()
			// elapsed = t.Sub(start)
			// result.ClientFinalize = float64(elapsed) / float64(time.Millisecond)
			fmt.Println("Crypten output", string(output))
		} else if config.UseEmp {
			fmt.Println("Using EMP")
			// start = time.Now()
			var ans ResponseMPC
			json.Unmarshal(ansValue, &ans)
			fmt.Println("The bucket size is", ans.BucketSize)
			fullCmd := fmt.Sprintf("\"/home/ubuntu/sbb-implementation/"+
				"emp-sh2pc/bin/test_example 1 12345 "+
				"/tmp/client_hash %v %v\"", config.Threshold, ans.BucketSize)
			fmt.Println("fullCmd", fullCmd)
			// empCmd := exec.Command("bash", "-c", fullCmd)
			empCmd := exec.Command("/home/ubuntu/sbb-implementation"+
				"/emp-sh2pc/bin/test_example", "1", "12345", "/tmp/client_hash",
				strconv.Itoa(config.Threshold), strconv.Itoa(ans.BucketSize))
			output, err := empCmd.Output()
			if err != nil {
				panic(err)
			}
			// t = time.Now()
			// elapsed = t.Sub(start)
			// result.ClientFinalize = float64(elapsed) / float64(time.Millisecond)
			fmt.Println("EMP output", string(output))
		} else { // Plaintext protocol
			start = time.Now()
			var ans ResponseTypeII
			json.Unmarshal(ansValue, &ans)

			hashbytes := input2ListBytes(ans.Hashes)
			var equals []int
			for i := range hashbytes {
				if hamming.Bytes(hashbytes[i], image) < config.Threshold {
					equals = append(equals, i)
				}
			}
			//fmt.Println("Answer:", equals)
			t = time.Now()
			elapsed = t.Sub(start)
			//fmt.Println("Client Side Finalize:", elapsed)
			result.ClientFinalize = float64(elapsed) / float64(time.Millisecond)
		}
	}
	t := time.Now()
	elapsed := t.Sub(totalStart)
	//fmt.Println("Client Side Total Time:", elapsed)
	result.ClientTotal = float64(elapsed) / float64(time.Millisecond)
	jsonData, _ := json.Marshal(result)
	fmt.Println(string(jsonData))
}
