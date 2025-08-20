-- ユーザー情報テーブル
CREATE TABLE user_infos (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  hashed_password TEXT NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'admin')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMP
);

-- 講師情報テーブル
CREATE TABLE teacher_profiles (
  id INTEGER PRIMARY KEY,  -- 使用与 user_infos.id 相同的 ID，作为一对一扩展
  phone TEXT,
  bio TEXT,
  profile_image TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (id) REFERENCES user_infos(id) ON DELETE CASCADE
);

-- 講義情報テーブル
CREATE TABLE lectures (
  id SERIAL PRIMARY KEY,
  teacher_id INTEGER NOT NULL,
  lecture_title TEXT NOT NULL,
  lecture_description TEXT,
  approval_status VARCHAR(20) DEFAULT 'pending' CHECK (
    approval_status IN ('pending', 'approved', 'rejected')
  ),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMP,

  FOREIGN KEY (teacher_id) REFERENCES teacher_profiles(id) ON DELETE CASCADE
);

-- 講義スケジュールテーブル
CREATE TABLE lecture_schedules (
  id SERIAL PRIMARY KEY,
  lecture_id INTEGER NOT NULL,
  booking_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_expired BOOLEAN DEFAULT FALSE,
  
  CHECK (start_time < end_time),
  UNIQUE (lecture_id, booking_date, start_time, end_time),

  FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
);

-- 講義予約テーブル
CREATE TABLE lecture_bookings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  lecture_id INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'pending' CHECK (
    status IN ('pending', 'confirmed', 'cancelled')
  ),
  booking_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_expired BOOLEAN DEFAULT FALSE,
  
  FOREIGN KEY (user_id) REFERENCES user_infos(id) ON DELETE CASCADE,
  FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
);

-- カルーセルテーブル
CREATE TABLE carousel (
  lecture_id INTEGER NOT NULL,
  display_order INTEGER NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  
  FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
);
