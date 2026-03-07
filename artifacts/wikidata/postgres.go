package main

import (
    "bufio"
    "database/sql"
    "fmt"
    "log"
    "os"
    "path/filepath"
    "runtime"
    "strings"
    "sync"
    "sync/atomic"
    "time"

    jsoniter "github.com/json-iterator/go"
    _ "github.com/lib/pq"
)

// 설정 상수
const (
    WIKIDATA_FILE = "/mnt/d/latest-all.json"      // <--- 여기를 수정
    PROGRESS_FILE = "geulso/wikidata/postgres_progress.txt"
    
    BATCH_SIZE = 1000                      // 배치 크기
    COMMIT_INTERVAL = 5000                 // 커밋 간격
    MAX_RETRY = 3                          // 재시도 횟수
    DELETE_ON_SUCCESS = false              // <--- 여기를 수정 (파일 삭제 비활성화)
)

var json = jsoniter.ConfigFastest

// 위키데이터 구조체
type WikidataItem struct {
    ID           string                       `json:"id"`
    Type         string                       `json:"type"`
    DataType     string                       `json:"datatype,omitempty"`
    Labels       map[string]Label             `json:"labels"`
    Descriptions map[string]Label             `json:"descriptions"`
    Aliases      map[string][]Label           `json:"aliases"`
    Claims       map[string]jsoniter.RawMessage `json:"claims"` // RawMessage로 지연 파싱
}

type Label struct {
    Language string `json:"language"`
    Value    string `json:"value"`
}

// 진행 상황 구조체
type Progress struct {
    CurrentFile   string    `json:"current_file"`
    CurrentLine   int       `json:"current_line"`
    ProcessedFiles []string `json:"processed_files"`
    DeletedFiles   []string `json:"deleted_files"`  // 삭제된 파일 목록 추가
    LastUpdate    time.Time `json:"last_update"`
}

// 통계 구조체
type Stats struct {
    TotalItems    int64
    TotalTriples  int64
    ErrorCount    int64
    CurrentFile   string
    StartTime     time.Time
    FileStartTime time.Time
    DeletedFiles  int64  // 삭제된 파일 수 추가
}

var stats Stats
var globalDB *sql.DB

func main() {
    // CPU 설정
    numCPU := runtime.NumCPU()
    runtime.GOMAXPROCS(numCPU)
    numWorkers := 20//numCPU/2 // CPU의 절반을 워커로 사용
    if numWorkers < 1 {
        numWorkers = 1
    }
    
    fmt.Println("=== 위키데이터 PostgreSQL 로더 (단일 파일 모드) ===")
    fmt.Printf("대상 파일: %s\n", WIKIDATA_FILE)
    fmt.Printf("CPU: %d개, 워커: %d개\n", numCPU, numWorkers)
    fmt.Printf("배치 크기: %d\n", BATCH_SIZE)
    
    // PostgreSQL 연결
    connStr := "host=localhost user=postgres password=test1224! dbname=geuldev sslmode=disable"
    db, err := sql.Open("postgres", connStr)
    if err != nil {
        log.Fatal("DB 연결 실패:", err)
    }
    defer db.Close()
    
    globalDB = db
    
    // 연결 풀 설정
    db.SetMaxOpenConns(numWorkers * 2)
    db.SetMaxIdleConns(numWorkers)
    db.SetConnMaxLifetime(time.Hour)
    
    if err := db.Ping(); err != nil {
        log.Fatal("DB ping 실패:", err)
    }
    fmt.Println("PostgreSQL 연결 성공!")
    
    // 진행 상황 로드
    progress := loadProgress()
    
    // 대상 파일 존재 여부 확인
    if _, err := os.Stat(WIKIDATA_FILE); os.IsNotExist(err) {
        log.Fatalf("대상 파일을 찾을 수 없습니다: %s", WIKIDATA_FILE)
    }
    
    // 이미 완료되었는지 확인 (CurrentLine을 -1로 설정하여 완료 표시)
    if progress.CurrentLine == -1 {
        fmt.Println("모든 작업이 이미 완료되었습니다. 프로그램을 종료합니다.")
        return
    }

    // 통계 초기화
    stats.StartTime = time.Now()
    stats.CurrentFile = filepath.Base(WIKIDATA_FILE)
    stats.FileStartTime = time.Now()
    
    // 진행 상황 저장 고루틴
    stopSaver := make(chan bool)
    go progressSaver(progress, stopSaver)
    
    // 통계 리포터 고루틴
    stopReporter := make(chan bool)
    go statsReporter(stopReporter)
    
    // === 파일 처리 시작 ===
    fmt.Printf("\n=== 파일 처리 시작: %s ===\n", stats.CurrentFile)
    startLine := progress.CurrentLine
    if startLine > 0 {
        fmt.Printf("라인 %d부터 재개합니다.\n", startLine)
    }
    
    // 파일 처리 실행
    success, err := processFile(WIKIDATA_FILE, startLine, numWorkers, progress)
    if err != nil {
        log.Fatalf("파일 처리 실패 %s: %v", WIKIDATA_FILE, err)
    }
    
    if success {
        fmt.Printf("\n파일 처리 완료: %s (소요시간: %v)\n", stats.CurrentFile, time.Since(stats.FileStartTime))
        
        // 진행 상황을 완료 상태로 업데이트 (-1은 완료를 의미)
        progress.CurrentLine = -1 
        progress.CurrentFile = "completed"
        saveProgress(progress)
        fmt.Println("진행 상황을 '완료'로 기록했습니다.")
    }
    
    // 고루틴 종료
    stopSaver <- true
    stopReporter <- true
    
    // 최종 통계 출력
    printFinalStats()
    
    fmt.Println("모든 처리 완료! 프로그램을 종료합니다.")
}

// 파일 처리
func processFile(filename string, startLine int, numWorkers int, progress *Progress) (bool, error) {
    file, err := os.Open(filename)
    if err != nil {
        return false, err
    }
    defer file.Close()
    
    scanner := bufio.NewScanner(file)
    scanner.Buffer(make([]byte, 0, 10*1024*1024), 10*1024*1024) // 10MB 버퍼
    
    // 워커 채널과 WaitGroup
    itemChan := make(chan []WikidataItem, numWorkers*2)
    var wg sync.WaitGroup
    
    // 워커 시작
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go worker(i, itemChan, &wg)
    }
    
    // 배치 처리
    batch := make([]WikidataItem, 0, BATCH_SIZE)
    lineNumber := 0
    hasError := false
    
    for scanner.Scan() {
        line := scanner.Text()
        lineNumber++
        
        // 시작 위치까지 스킵
        if lineNumber <= startLine {
            continue
        }
        
        // JSON 배열 시작/끝 처리
        line = strings.TrimSpace(line)
        if line == "[" || line == "]" || line == "" {
            continue
        }
        
        // 콤마 제거
        line = strings.TrimSuffix(line, ",")
        
        // JSON 파싱 (json-iterator 사용)
        var item WikidataItem
        if err := json.Unmarshal([]byte(line), &item); err != nil {
            atomic.AddInt64(&stats.ErrorCount, 1)
            if atomic.LoadInt64(&stats.ErrorCount) % 100 == 0 {
                log.Printf("파싱 에러 (총 %d건): %v", stats.ErrorCount, err)
            }
            continue
        }
        
        batch = append(batch, item)
        
        // 배치가 차면 워커에게 전송
        if len(batch) >= BATCH_SIZE {
            itemChan <- batch
            batch = make([]WikidataItem, 0, BATCH_SIZE)
        }
        
        // 진행 상황 업데이트
        if lineNumber % 1000 == 0 {
            progress.CurrentFile = filepath.Base(filename)
            progress.CurrentLine = lineNumber
            progress.LastUpdate = time.Now()
        }
    }
    
    // 남은 배치 처리
    if len(batch) > 0 {
        itemChan <- batch
    }
    
    // 워커 종료 대기
    close(itemChan)
    wg.Wait()
    
    if err := scanner.Err(); err != nil {
        hasError = true
        return false, err
    }
    
    return !hasError, nil
}

// 워커 함수
func worker(id int, itemChan <-chan []WikidataItem, wg *sync.WaitGroup) {
    defer wg.Done()
    
    for batch := range itemChan {
        processBatch(id, batch)
    }
}

// 배치 처리
func processBatch(workerID int, batch []WikidataItem) {
    tx, err := globalDB.Begin()
    if err != nil {
        log.Printf("워커 %d: 트랜잭션 시작 실패: %v", workerID, err)
        return
    }
    defer tx.Rollback()
    
    // Prepared statements
    stmts, err := prepareStatements(tx)
    if err != nil {
        log.Printf("워커 %d: Statement 준비 실패: %v", workerID, err)
        return
    }
    defer closeStatements(stmts)
    
    itemCount := 0
    tripleCount := int64(0)
    
    for _, item := range batch {
        // entities 테이블
        if _, err := stmts["entity"].Exec(item.ID, item.Type); err != nil {
            // 중복 키 에러는 무시
            if !strings.Contains(err.Error(), "duplicate key") {
                log.Printf("Entity 삽입 실패 %s: %v", item.ID, err)
            }
            continue
        }
        
        // labels 테이블
        for lang, label := range item.Labels {
            stmts["label"].Exec(item.ID, lang, label.Value)
        }
        
        // descriptions 테이블
        for lang, desc := range item.Descriptions {
            stmts["desc"].Exec(item.ID, lang, desc.Value)
        }
        
        // aliases 테이블
        for lang, aliases := range item.Aliases {
            for order, alias := range aliases {
                stmts["alias"].Exec(item.ID, lang, alias.Value, order)
            }
        }
        
        // properties_meta 테이블 (속성인 경우)
        if strings.HasPrefix(item.ID, "P") && item.Type == "property" {
            labelEn := ""
            descEn := ""
            if l, ok := item.Labels["en"]; ok {
                labelEn = l.Value
            }
            if d, ok := item.Descriptions["en"]; ok {
                descEn = d.Value
            }
            stmts["prop_meta"].Exec(item.ID, item.DataType, labelEn, descEn)
        }
        
        // claims 처리
        for property, claimRaw := range item.Claims {
            count := processClaimsOptimized(item.ID, property, claimRaw, stmts)
            tripleCount += count
        }
        
        itemCount++
    }
    
    // 커밋
    if err := tx.Commit(); err != nil {
        log.Printf("워커 %d: 커밋 실패: %v", workerID, err)
    } else {
        atomic.AddInt64(&stats.TotalItems, int64(itemCount))
        atomic.AddInt64(&stats.TotalTriples, tripleCount)
    }
}

// 최적화된 Claims 처리
func processClaimsOptimized(subject, property string, claimRaw jsoniter.RawMessage, stmts map[string]*sql.Stmt) int64 {
    var claims []map[string]jsoniter.RawMessage
    if err := json.Unmarshal(claimRaw, &claims); err != nil {
        return 0
    }
    
    count := int64(0)
    for _, claim := range claims {
        // rank 추출
        rank := "normal"
        if rankRaw, ok := claim["rank"]; ok {
            json.Unmarshal(rankRaw, &rank)
        }
        
        // mainsnak 처리
        if mainsnakRaw, ok := claim["mainsnak"]; ok {
            var mainsnak map[string]jsoniter.RawMessage
            if err := json.Unmarshal(mainsnakRaw, &mainsnak); err != nil {
                continue
            }
            
            objectValue, objectType := extractValueOptimized(mainsnak)
            
            var tripleID int64 // tripleID를 저장할 변수

            // 트리플 삽입 후 RETURNING id 값을 스캔
            err := stmts["triple"].QueryRow(subject, property, objectValue, objectType, rank).Scan(&tripleID)
            if err != nil {
                // 에러 발생 시 로그를 남기고 다음 claim으로 넘어감
                // log.Printf("트리플 삽입 실패: %v", err) 
                continue
            }
            
            count++
            
            // Qualifiers 처리
            if qualifiersRaw, ok := claim["qualifiers"]; ok {
                processQualifiersOptimized(tripleID, qualifiersRaw, stmts["qualifier"])
            }
            
            // hierarchy 테이블
            if property == "P31" || property == "P279" {
                if datavalueRaw, ok := mainsnak["datavalue"]; ok {
                    var datavalue map[string]jsoniter.RawMessage
                    if json.Unmarshal(datavalueRaw, &datavalue) == nil {
                        if valueRaw, ok := datavalue["value"]; ok {
                            var value map[string]string
                            if json.Unmarshal(valueRaw, &value) == nil {
                                if id, ok := value["id"]; ok {
                                    stmts["hierarchy"].Exec(subject, id, property)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return count
}

// 값 추출 최적화
func extractValueOptimized(mainsnak map[string]jsoniter.RawMessage) (string, string) {
    objectValue := ""
    objectType := ""
    
    // datatype 추출
    if datatypeRaw, ok := mainsnak["datatype"]; ok {
        json.Unmarshal(datatypeRaw, &objectType)
    }
    
    // datavalue 추출
    if datavalueRaw, ok := mainsnak["datavalue"]; ok {
        var datavalue map[string]jsoniter.RawMessage
        if err := json.Unmarshal(datavalueRaw, &datavalue); err != nil {
            return objectValue, objectType
        }
        
        // type 확인
        if typeRaw, ok := datavalue["type"]; ok {
            var valueType string
            json.Unmarshal(typeRaw, &valueType)
            objectType = valueType
        }
        
        // value 처리
        if valueRaw, ok := datavalue["value"]; ok {
            // 문자열인 경우
            var strValue string
            if err := json.Unmarshal(valueRaw, &strValue); err == nil {
                objectValue = strValue
            } else {
                // 객체인 경우
                var objValue map[string]jsoniter.RawMessage
                if err := json.Unmarshal(valueRaw, &objValue); err == nil {
                    // id 필드 우선
                    if idRaw, ok := objValue["id"]; ok {
                        json.Unmarshal(idRaw, &objectValue)
                    } else if amountRaw, ok := objValue["amount"]; ok {
                        json.Unmarshal(amountRaw, &objectValue)
                    } else {
                        objectValue = string(valueRaw)
                    }
                } else {
                    objectValue = string(valueRaw)
                }
            }
        }
    }
    
    return objectValue, objectType
}

// Qualifiers 처리 최적화
func processQualifiersOptimized(tripleID int64, qualifiersRaw jsoniter.RawMessage, stmt *sql.Stmt) {
    var qualifiers map[string][]map[string]jsoniter.RawMessage
    if err := json.Unmarshal(qualifiersRaw, &qualifiers); err != nil {
        return
    }
    
    for prop, qualList := range qualifiers {
        for _, qual := range qualList {
            if datavalueRaw, ok := qual["datavalue"]; ok {
                var datavalue map[string]jsoniter.RawMessage
                if json.Unmarshal(datavalueRaw, &datavalue) == nil {
                    value, datatype := extractValueFromDatavalue(datavalue)
                    stmt.Exec(tripleID, prop, value, datatype)
                }
            }
        }
    }
}

// datavalue에서 값 추출
func extractValueFromDatavalue(datavalue map[string]jsoniter.RawMessage) (string, string) {
    value := ""
    datatype := ""
    
    if typeRaw, ok := datavalue["type"]; ok {
        json.Unmarshal(typeRaw, &datatype)
    }
    
    if valueRaw, ok := datavalue["value"]; ok {
        if err := json.Unmarshal(valueRaw, &value); err != nil {
            value = string(valueRaw)
        }
    }
    
    return value, datatype
}

// Prepared statements 생성
func prepareStatements(tx *sql.Tx) (map[string]*sql.Stmt, error) {
    stmts := make(map[string]*sql.Stmt)
    
    queries := map[string]string{
        "entity": "INSERT INTO entities (id, type) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        "label": "INSERT INTO entity_labels (entity_id, language, label) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        "desc": "INSERT INTO entity_descriptions (entity_id, language, description) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        "alias": "INSERT INTO entity_aliases (entity_id, language, alias, alias_order) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
        "triple": "INSERT INTO triples (subject, property, object_value, object_type, rank) VALUES ($1, $2, $3, $4, $5) RETURNING id",
        "qualifier": "INSERT INTO triple_qualifiers (triple_id, property, value, datatype) VALUES ($1, $2, $3, $4)",
        "hierarchy": "INSERT INTO hierarchy (child, parent, property) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        "prop_meta": "INSERT INTO properties_meta (property_id, datatype, label_en, description_en) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
    }
    
    for name, query := range queries {
        stmt, err := tx.Prepare(query)
        if err != nil {
            return nil, fmt.Errorf("%s 준비 실패: %v", name, err)
        }
        stmts[name] = stmt
    }
    
    return stmts, nil
}

// Statements 닫기
func closeStatements(stmts map[string]*sql.Stmt) {
    for _, stmt := range stmts {
        if stmt != nil {
            stmt.Close()
        }
    }
}

// 진행 상황 로드
func loadProgress() *Progress {
    progress := &Progress{
        ProcessedFiles: make([]string, 0),
        DeletedFiles: make([]string, 0),
    }
    
    data, err := os.ReadFile(PROGRESS_FILE)
    if err != nil {
        return progress
    }
    
    if err := json.Unmarshal(data, progress); err != nil {
        log.Printf("진행 상황 파싱 실패: %v", err)
        return &Progress{
            ProcessedFiles: make([]string, 0),
            DeletedFiles: make([]string, 0),
        }
    }
    
    return progress
}

// 진행 상황 저장
func saveProgress(progress *Progress) {
    progress.LastUpdate = time.Now()
    data, err := json.MarshalIndent(progress, "", "  ")
    if err != nil {
        log.Printf("진행 상황 직렬화 실패: %v", err)
        return
    }
    
    if err := os.WriteFile(PROGRESS_FILE, data, 0644); err != nil {
        log.Printf("진행 상황 저장 실패: %v", err)
    }
}

// 진행 상황 자동 저장
func progressSaver(progress *Progress, stop <-chan bool) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()
    
    for {
        select {
        case <-ticker.C:
            saveProgress(progress)
        case <-stop:
            saveProgress(progress)
            return
        }
    }
}

// 통계 리포터
func statsReporter(stop <-chan bool) {
    ticker := time.NewTicker(10 * time.Second)
    defer ticker.Stop()
    
    lastItems := int64(0)
    lastTriples := int64(0)
    
    for {
        select {
        case <-ticker.C:
            items := atomic.LoadInt64(&stats.TotalItems)
            triples := atomic.LoadInt64(&stats.TotalTriples)
            errors := atomic.LoadInt64(&stats.ErrorCount)
            deletedFiles := atomic.LoadInt64(&stats.DeletedFiles)
            
            itemSpeed := float64(items-lastItems) / 10.0
            tripleSpeed := float64(triples-lastTriples) / 10.0
            
            elapsed := time.Since(stats.StartTime)
            avgItemSpeed := float64(items) / elapsed.Seconds()
            avgTripleSpeed := float64(triples) / elapsed.Seconds()
            
            fmt.Printf("[%s] 파일: %s | 엔티티: %d (%.0f/초) | 트리플: %d (%.0f/초) | 에러: %d | 삭제: %d\n",
                time.Now().Format("15:04:05"),
                stats.CurrentFile,
                items, itemSpeed,
                triples, tripleSpeed,
                errors,
                deletedFiles)
            
            if itemSpeed > 0 {
                remainingEstimate := float64(100000-items%100000) / avgItemSpeed
                fmt.Printf("  예상 완료 시간: %.1f분 | 평균: 엔티티 %.0f/초, 트리플 %.0f/초\n",
                    remainingEstimate/60, avgItemSpeed, avgTripleSpeed)
            }
            
            lastItems = items
            lastTriples = triples
            
        case <-stop:
            return
        }
    }
}

// 최종 통계 출력
func printFinalStats() {
    totalTime := time.Since(stats.StartTime)
    items := atomic.LoadInt64(&stats.TotalItems)
    triples := atomic.LoadInt64(&stats.TotalTriples)
    errors := atomic.LoadInt64(&stats.ErrorCount)
    deletedFiles := atomic.LoadInt64(&stats.DeletedFiles)
    
    fmt.Println("\n========== 처리 완료 ==========")
    fmt.Printf("총 엔티티: %d개\n", items)
    fmt.Printf("총 트리플: %d개\n", triples)
    fmt.Printf("에러: %d건\n", errors)
    fmt.Printf("삭제된 파일: %d개\n", deletedFiles)
    fmt.Printf("소요 시간: %v\n", totalTime)
    fmt.Printf("평균 속도: %.0f 엔티티/초, %.0f 트리플/초\n",
        float64(items)/totalTime.Seconds(),
        float64(triples)/totalTime.Seconds())
    fmt.Println("==============================")
}