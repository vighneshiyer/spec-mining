// See README.md for license details.

package examples

import chisel3.iotesters.{ChiselFlatSpec, Driver, PeekPokeTester}
import org.scalatest.FreeSpec

import util.Random

class LifeTests(c: Life) extends PeekPokeTester(c) {
  // Disable printing when peeking state variables

  def setMode(run: Boolean): Unit = {
    poke(c.io.running, run)
    step(1)
  }

  def clear_board(): Unit = {
    poke(c.io.writeValue, 0)

    for {
      i <- 0 until c.rows
      j <- 0 until c.cols
    } {
      poke(c.io.writeRowAddress, i)
      poke(c.io.writeColAddress, j)
      step(1)
    }
  }

  def initBlinker(): Unit = {
    clear_board()

    poke(c.io.writeValue, 1)
    poke(c.io.writeRowAddress, 3)
    for(addr <- Seq(3, 5)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }
    poke(c.io.writeRowAddress, 4)
    for(addr <- Seq(4, 5)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }
    poke(c.io.writeRowAddress, 5)
    for(addr <- Seq(4)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }

  }

  def initGlider(): Unit = {
    clear_board()

    poke(c.io.writeValue, 1)
    poke(c.io.writeRowAddress, 3)
    for(addr <- Seq(3, 5)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }
    poke(c.io.writeRowAddress, 4)
    for(addr <- Seq(4, 5)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }
    poke(c.io.writeRowAddress, 5)
    for(addr <- Seq(4)) {
      poke(c.io.writeColAddress, addr)
      step(1)
    }
  }

  def randomize(): Unit = {
    clear_board()

    for(addr <- 0 until c.rows * c.rows) {
      poke(c.io.writeValue, Random.nextBoolean())
      poke(c.io.writeRowAddress, addr)
      step(1)
    }
  }

  def printBoard(): Unit = {
    // Print column number
    print("   ")
    for (i <- 0 until c.cols)
      print(" " + i.toString.last)
    println()

    for(i <- 0 until c.rows) {
      // Print line number
      print(f"$i%2d")
      print(" ")

      // Print cell state
      for {
        j <- 0 until c.cols
      } {
        val s = peek(c.io.state(i)(j))
        if (s == 1)
          print(" *")
        else
          print("  ")
      }

      println()
    }
    println()
  }

  setMode(run = false)
  // uncomment one of these
  //  initBlinker
  initGlider()
  //  randomize()
  printBoard()

  setMode(run = true)

  for(time <- 0 until 100) {
    println(s"Period: $time")
    printBoard()
    step(1)
  }
}

class LifeTester extends ChiselFlatSpec {
  "LifeTester" should "generate a VCD trace" in {
    Driver.execute(
      Array("--backend-name", "verilator", "--generate-vcd-output", "on", "--target-dir", "vcd/life", "--top-name", "life"),
      () => new Life(10, 10)
    ) {
      c => new LifeTests(c)
    } should be(true)
  }
}
