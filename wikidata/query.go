package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/jackc/pgx/v4/pgxpool"
)

// --- 설정 ---
const (
	// 데이터베이스 연결 정보
	CONN_STR = "host=localhost user=postgres password=test1224! dbname=geuldev sslmode=disable"
)

func main() {
	// --- 1. 커맨드 라인 플래그 정의 ---
	path := flag.String("path", "", "결과를 저장할 JSON 파일 경로 (필수)")
	query := flag.String("query", "", "실행할 SELECT 쿼리 문자열")
	queryPath := flag.String("query-path", "", "실행할 SELECT 쿼리가 담긴 파일 경로")

	flag.Parse()

	// --- 2. 플래그 유효성 검사 ---
	if *path == "" {
		log.Fatal("오류: --path 플래그는 필수입니다.")
	}
	if (*query == "" && *queryPath == "") || (*query != "" && *queryPath != "") {
		log.Fatal("오류: --query 또는 --query-path 중 하나만 사용해야 합니다.")
	}

	// --- 3. 실행할 쿼리 목록 준비 ---
	var queries []string
	if *query != "" {
		queries = append(queries, *query)
	} else {
		queryBytes, err := os.ReadFile(*queryPath)
		if err != nil {
			log.Fatalf("쿼리 파일을 읽는 데 실패했습니다: %v", err)
		}
		// 세미콜론(;)을 기준으로 쿼리 분리
		queries = strings.Split(string(queryBytes), ";")
	}

	// --- 4. 데이터베이스 연결 ---
	dbpool, err := pgxpool.Connect(context.Background(), CONN_STR)
	if err != nil {
		log.Fatalf("DB 연결 실패: %v", err)
	}
	defer dbpool.Close()
	fmt.Println("PostgreSQL 연결 성공!")

	// --- 5. 각 쿼리 실행 및 결과 저장 ---
	queryCount := 0
	for i, q := range queries {
		trimmedQuery := strings.TrimSpace(q)
		if trimmedQuery == "" {
			continue // 빈 쿼리는 건너뜀
		}
		queryCount++

		// --- 출력 파일 경로 결정 ---
		outputPath := *path
		if len(queries) > 1 && queryCount > 1 {
			// 쿼리가 여러 개일 경우, 파일명에 인덱스 추가
			ext := filepath.Ext(outputPath)
			base := strings.TrimSuffix(outputPath, ext)
			outputPath = fmt.Sprintf("%s_%d%s", base, i+1, ext)
		}

		fmt.Printf("\n[%d/%d] 쿼리 실행 중...\n", queryCount, len(queries))
		fmt.Printf("결과 저장 경로: %s\n", outputPath)

		// --- 쿼리 실행 및 결과 처리 ---
		err := executeAndSave(dbpool, trimmedQuery, outputPath)
		if err != nil {
			log.Printf("오류: 쿼리 %d 실행 실패: %v", i+1, err)
		} else {
			fmt.Printf("성공: 결과가 %s 파일에 저장되었습니다.\n", outputPath)
		}
	}
	fmt.Println("\n모든 작업 완료!")
}

// 쿼리를 실행하고 결과를 JSON 파일로 저장하는 함수
func executeAndSave(dbpool *pgxpool.Pool, query string, outputPath string) error {
	rows, err := dbpool.Query(context.Background(), query)
	if err != nil {
		return fmt.Errorf("쿼리 실행 오류: %w", err)
	}
	defer rows.Close()

	// 컬럼 이름 가져오기
	fields := rows.FieldDescriptions()
	var columns []string
	for _, field := range fields {
		columns = append(columns, string(field.Name))
	}

	var results []map[string]interface{}
	for rows.Next() {
		// 각 행의 값을 스캔
		values, err := rows.Values()
		if err != nil {
			return fmt.Errorf("행 스캔 오류: %w", err)
		}

		// 맵으로 변환
		rowMap := make(map[string]interface{})
		for i, colName := range columns {
			rowMap[colName] = values[i]
		}
		results = append(results, rowMap)
	}

	// JSON으로 변환 (Pretty Print)
	jsonData, err := json.MarshalIndent(results, "", "  ")
	if err != nil {
		return fmt.Errorf("JSON 변환 오류: %w", err)
	}

	// 파일에 저장
	err = os.WriteFile(outputPath, jsonData, 0644)
	if err != nil {
		return fmt.Errorf("파일 쓰기 오류: %w", err)
	}

	return nil
}