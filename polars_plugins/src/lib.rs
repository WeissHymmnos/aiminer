use polars::prelude::*;
use pyo3::prelude::*;
use pyo3_polars::derive::polars_expr;
use serde::Deserialize;
use rayon::prelude::*;
use nom::{
    IResult,
    sequence::{delimited, tuple, pair},
    character::complete::{char, multispace0, digit1},
    bytes::complete::{tag, take_while1},
    branch::alt,
    multi::{separated_list0, many0},
    combinator::{map, recognize, opt},
};

#[derive(Deserialize)]
struct WindowKwargs { window_size: usize }

#[polars_expr(output_type=Float64)]
fn ts_rank(inputs: &[Series], kwargs: WindowKwargs) -> PolarsResult<Series> {
    let ca = inputs[0].f64()?;
    let window_size = kwargs.window_size;
    let len = ca.len();

    if window_size == 0 || len == 0 {
        return Ok(Float64Chunked::full_null(ca.name().clone(), len).into_series());
    }

    let vals: Vec<Option<f64>> = ca.into_iter().collect();

    let out: Vec<Option<f64>> = (0..len).into_par_iter().map(|i| {
        if i + 1 < window_size {
            return None;
        }
        let last = vals[i];
        let last_val = match last {
            Some(v) if !v.is_nan() => v,
            _ => return None,
        };

        let mut count = 0;
        let mut rank = 0;
        let start = i + 1 - window_size;
        
        for j in start..=i {
            if let Some(v) = vals[j] {
                if !v.is_nan() {
                    count += 1;
                    if v <= last_val { rank += 1; }
                }
            }
        }
        
        if count == 0 { None } else { Some(rank as f64 / count as f64) }
    }).collect();

    Ok(Float64Chunked::from_iter(out).into_series())
}

#[polars_expr(output_type=Int64)]
fn ts_argmax(inputs: &[Series], kwargs: WindowKwargs) -> PolarsResult<Series> {
    let ca = inputs[0].f64()?;
    let window_size = kwargs.window_size;
    let len = ca.len();

    if window_size == 0 || len == 0 {
        return Ok(Int64Chunked::full_null(ca.name().clone(), len).into_series());
    }

    let vals: Vec<Option<f64>> = ca.into_iter().collect();

    let out: Vec<Option<i64>> = (0..len).into_par_iter().map(|i| {
        if i + 1 < window_size { return None; }
        let start = i + 1 - window_size;
        let mut max_v = f64::NEG_INFINITY;
        let mut max_i = 0;
        let mut found = false;
        
        for j in 0..window_size {
            if let Some(v) = vals[start + j] {
                if !v.is_nan() {
                    if !found || v > max_v {
                        max_v = v;
                        max_i = j as i64;
                        found = true;
                    }
                }
            }
        }
        if found { Some(max_i) } else { None }
    }).collect();

    Ok(Int64Chunked::from_iter(out).into_series())
}

#[polars_expr(output_type=Int64)]
fn ts_argmin(inputs: &[Series], kwargs: WindowKwargs) -> PolarsResult<Series> {
    let ca = inputs[0].f64()?;
    let window_size = kwargs.window_size;
    let len = ca.len();

    if window_size == 0 || len == 0 {
        return Ok(Int64Chunked::full_null(ca.name().clone(), len).into_series());
    }

    let vals: Vec<Option<f64>> = ca.into_iter().collect();

    let out: Vec<Option<i64>> = (0..len).into_par_iter().map(|i| {
        if i + 1 < window_size { return None; }
        let start = i + 1 - window_size;
        let mut min_v = f64::INFINITY;
        let mut min_i = 0;
        let mut found = false;
        
        for j in 0..window_size {
            if let Some(v) = vals[start + j] {
                if !v.is_nan() {
                    if !found || v < min_v {
                        min_v = v;
                        min_i = j as i64;
                        found = true;
                    }
                }
            }
        }
        if found { Some(min_i) } else { None }
    }).collect();

    Ok(Int64Chunked::from_iter(out).into_series())
}

#[derive(Debug, Clone)]
enum Expr {
    Literal(String),
    Field(String),
    Binary(Box<Expr>, String, Box<Expr>),
    Call(String, Vec<Expr>),
}

fn identifier(input: &str) -> IResult<&str, String> {
    map(take_while1(|c: char| c.is_alphanumeric() || c == '_' || c == '.'), |s: &str| s.to_string())(input)
}

fn number(input: &str) -> IResult<&str, Expr> {
    map(recognize(tuple((opt(char('-')), digit1, opt(pair(char('.'), digit1))))), |s: &str| Expr::Literal(s.to_string()))(input)
}

fn unary_neg(input: &str) -> IResult<&str, Expr> {
    let (input, _) = char('-')(input)?;
    let (input, _) = multispace0(input)?;
    let (input, expr) = primary(input)?;
    Ok((input, Expr::Call("Neg".to_string(), vec![expr])))
}

fn primary(input: &str) -> IResult<&str, Expr> {
    alt((
        parse_call,
        delimited(tuple((char('('), multispace0)), parse_expression, tuple((multispace0, char(')')))),
        map(tuple((char('$'), identifier)), |(_, name)| Expr::Field(name)),
        number,
        unary_neg,
        map(identifier, |s| if s.contains('.') { Expr::Literal(s) } else { Expr::Literal(format!("'{}'", s)) }),
    ))(input)
}

fn parse_call(input: &str) -> IResult<&str, Expr> {
    let (input, name) = identifier(input)?;
    let (input, _) = multispace0(input)?;
    let (input, args) = delimited(
        char('('),
        separated_list0(tuple((multispace0, char(','), multispace0)), parse_expression),
        char(')')
    )(input)?;
    Ok((input, Expr::Call(name, args)))
}

fn term(input: &str) -> IResult<&str, Expr> {
    let (input, mut left) = primary(input)?;
    let (input, remaining) = many0(tuple((
        multispace0,
        alt((tag("*"), tag("/"), tag("&"), tag("|"))),
        multispace0,
        primary
    )))(input)?;
    for (_, op, _, right) in remaining {
        left = Expr::Binary(Box::new(left), op.to_string(), Box::new(right));
    }
    Ok((input, left))
}

fn parse_expression(input: &str) -> IResult<&str, Expr> {
    let (input, mut left) = term(input)?;
    let (input, remaining) = many0(tuple((
        multispace0,
        alt((tag("+"), tag("-"), tag(">="), tag("<="), tag(">"), tag("<"), tag("=="), tag("!="))),
        multispace0,
        term
    )))(input)?;
    for (_, op, _, right) in remaining {
        left = Expr::Binary(Box::new(left), op.to_string(), Box::new(right));
    }
    Ok((input, left))
}

fn to_python(expr: Expr) -> String {
    match expr {
        Expr::Literal(s) => s,
        Expr::Field(s) => format!("pl.col('{}')", s),
        Expr::Binary(left, op, right) => {
            let l = to_python(*left);
            let r = to_python(*right);
            match op.as_str() {
                "+" => format!("({} + {})", l, r),
                "-" => format!("({} - {})", l, r),
                "*" => format!("({} * {})", l, r),
                "/" => format!("({} / {})", l, r),
                ">" => format!("({} > {})", l, r),
                "<" => format!("({} < {})", l, r),
                ">=" => format!("({} >= {})", l, r),
                "<=" => format!("({} <= {})", l, r),
                "==" => format!("({} == {})", l, r),
                "!=" => format!("({} != {})", l, r),
                "&" => format!("({} & {})", l, r),
                "|" => format!("({} | {})", l, r),
                _ => format!("{}({}, {})", op, l, r),
            }
        },
        Expr::Call(name, args) => {
            let args_str: Vec<String> = args.into_iter().map(to_python).collect();
            format!("{}({})", name, args_str.join(", "))
        }
    }
}

#[pyfunction]
fn compile_alpha(expression: String) -> PyResult<String> {
    let trimmed = expression.trim();
    match parse_expression(trimmed) {
        Ok((remaining, expr)) => {
            if !remaining.trim().is_empty() {
                return Ok(format!("Error: Unparsed trailing input: '{}'", remaining));
            }
            Ok(to_python(expr))
        },
        Err(e) => Ok(format!("Error: {:?}", e)),
    }
}

#[pymodule]
fn polars_plugins(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.1.0")?;
    m.add_function(wrap_pyfunction!(compile_alpha, m)?)?;
    Ok(())
}

